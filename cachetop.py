#!/usr/bin/env python3
"""
cachetop - Real-time LVM cache monitoring tool similar to htop
Shows cache usage, hit ratios, dirty LVM blocks, and dirty data in RAM

Version: 2025.07
Author: Jerico Thomas
License: MIT
"""

import subprocess
import time
import os
import sys
from collections import deque
import contextlib
import glob
import io
import re
import select
import threading
import termios
import tty

# Skip sudo when already root (so `sudo cachetop` never nests sudo prompts)
SUDO = [] if os.geteuid() == 0 else ['sudo']

# Fixed layout: everything stays inside MAX_WIDTH columns.
MAX_WIDTH = 100  # right edge of the whole display (needs a terminal at least this wide)
BAR_WIDTH = 60   # every percentage bar; leaves room for the longest label after it
# Pipeline diagram: 1 + 3 stage boxes + 2 gaps + 7-column branch + drive box = 99 columns
PIPE_STAGE_INNER = 15
PIPE_DRIVE_INNER = 20
PIPE_GAP = 5
REFRESH_STEPS = (0.25, 0.5, 0.75, 1, 2, 4, 8, 10)   # seconds; the + / - keys move between these
DRIVE_RATE_WINDOW = 5.0   # seconds; drive speeds are averaged over this long so bursts do not flicker

def dm_device_name(vg, lv):
    """Device-mapper name of an LV ('-' is doubled inside names)"""
    return f"{vg.replace('-', '--')}-{lv.replace('-', '--')}"


class LVMCacheMonitor:
    def __init__(self, vg_name="vg_games", lv_name="games"):
        self.vg_name = vg_name
        self.lv_name = lv_name
        
        # Memory / backing-disk sampling state
        self.disk_names = {'hdd': None, 'cache': None}
        self.disk_checked = False
        self.use_dmsetup = True      # cheap kernel query; falls back to lvs if unusable
        self.disk_snaps = {'hdd': deque(), 'cache': deque()}   # (time, counters) for the drive-speed window
        self.refresh_interval = 1.0
        self.prev_sample = None
        self.drain_history = deque(maxlen=5)  # recent drain rates (kB/s), smooths the ETA
        self.cache_drain_history = deque(maxlen=10)  # same, for dirty LVM cache blocks (bytes/s)
        self.prev_cache = None                       # (time, dirty_blocks) from the last refresh
        self.prev_migration = None                   # (time, promotions, demotions) from the last refresh
        self.promo_history = deque(maxlen=10)        # recent copy-in rates (bytes/s)
        self.demo_history = deque(maxlen=10)         # recent eviction rates (bytes/s)
        self.lazyinit_pid = None                     # pid of the ext4lazyinit kernel thread, once found
        self.lazyinit_next_scan = 0.0                # next time we may rescan /proc for it
        self.lazyinit = {'seen': False, 'busy': False, 'next': 0.0, 'zeroed': None, 'total': None,
                         'history': deque(maxlen=60)}  # (time, zeroed) samples, one a minute
        
        # Terminal colors
        self.colors = {
            'reset': '\033[0m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'red': '\033[91m',
            'blue': '\033[94m',
            'cyan': '\033[96m',
            'bold': '\033[1m',
            'dim': '\033[2m'
        }

    def get_dynamic_widths(self):
        """Fixed layout widths (kept as a method so callers do not change)"""
        return {'bar_width': BAR_WIDTH, 'terminal_width': MAX_WIDTH}

    def parse_dm_cache_status(self, text):
        """Parse `dmsetup status` for a dm-cache target (kernel doc: cache.rst)"""
        for line in text.splitlines():
            p = line.split()
            if len(p) < 16 or p[2] != 'cache':
                continue
            try:
                used, total = (int(x) for x in p[6].split('/'))
                features = p[15:15 + int(p[14])]
                mode = next((f for f in features if f in ('writeback', 'writethrough', 'passthrough')), 'unknown')
                return {
                    'total_blocks': total, 'used_blocks': used, 'dirty_blocks': int(p[13]),
                    'read_hits': int(p[7]), 'read_misses': int(p[8]),
                    'write_hits': int(p[9]), 'write_misses': int(p[10]),
                    'block_size': int(p[5]) * 512, 'cache_mode': mode,
                    'demotions': int(p[11]), 'promotions': int(p[12]),
                }
            except (ValueError, IndexError):
                continue
        return None

    def read_cache_counters_lvs(self):
        """Slower fallback: ask LVM (chunk_size gives the cache block size)"""
        cmd = [
            *SUDO, 'lvs', '--noheadings', '--nosuffix', '--units', 'b',
            '-o', 'cache_total_blocks,cache_used_blocks,cache_dirty_blocks,cache_read_hits,cache_read_misses,cache_write_hits,cache_write_misses,chunk_size,cache_mode',
            f'{self.vg_name}/{self.lv_name}'
        ]
        try:
            values = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10).stdout.split()
            if len(values) < 9:
                return None
            return {
                'total_blocks': int(values[0]), 'used_blocks': int(values[1]), 'dirty_blocks': int(values[2]),
                'read_hits': int(values[3]), 'read_misses': int(values[4]),
                'write_hits': int(values[5]), 'write_misses': int(values[6]),
                'block_size': int(float(values[7])) or 4096, 'cache_mode': values[8],
                'demotions': None, 'promotions': None,   # lvs does not report these
            }
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, ValueError, IndexError):
            return None

    def read_cache_counters(self):
        """Raw cache counters. `dmsetup status` is a single quick kernel query with
        no LVM scan or locking; `lvs` is only used if that does not work."""
        if self.use_dmsetup:
            try:
                out = subprocess.run(
                    [*SUDO, 'dmsetup', 'status', dm_device_name(self.vg_name, self.lv_name)],
                    capture_output=True, text=True, check=True, timeout=5).stdout
                raw = self.parse_dm_cache_status(out)
                if raw:
                    return raw
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                pass
            self.use_dmsetup = False
        return self.read_cache_counters_lvs()

    def get_lvm_cache_stats(self):
        """Get LVM cache statistics"""
        raw = self.read_cache_counters()
        if not raw:
            return None
        total_blocks = raw['total_blocks']
        used_blocks = raw['used_blocks']
        dirty_blocks = raw['dirty_blocks']
        read_hits = raw['read_hits']
        read_misses = raw['read_misses']
        write_hits = raw['write_hits']
        write_misses = raw['write_misses']
        block_size = raw['block_size']
        pool_size_bytes = total_blocks * block_size
        # Calculate percentages and ratios
        cache_usage_pct = (used_blocks / total_blocks * 100) if total_blocks > 0 else 0
        dirty_ratio_pct = (dirty_blocks / total_blocks * 100) if total_blocks > 0 else 0
        
        total_reads = read_hits + read_misses
        total_writes = write_hits + write_misses
        total_ops = total_reads + total_writes
        
        hit_ratio_pct = ((read_hits + write_hits) / total_ops * 100) if total_ops > 0 else 0
        read_hit_ratio_pct = (read_hits / total_reads * 100) if total_reads > 0 else 0
        write_hit_ratio_pct = (write_hits / total_writes * 100) if total_writes > 0 else 0
        
        # How fast are dirty cache blocks being flushed to the HDD, and when will they be clear?
        now = time.monotonic()
        dirty_drain_bps = None
        dirty_eta = None
        if dirty_blocks == 0:
            self.cache_drain_history.clear()
        elif self.prev_cache:
            dt = now - self.prev_cache[0]
            if dt > 0:
                self.cache_drain_history.append((self.prev_cache[1] - dirty_blocks) * block_size / dt)
                dirty_drain_bps = sum(self.cache_drain_history) / len(self.cache_drain_history)
                if dirty_drain_bps > 65536:  # flushing faster than 64 KiB/s
                    dirty_eta = dirty_blocks * block_size / dirty_drain_bps
        self.prev_cache = (now, dirty_blocks)

        # Blocks copied into the cache (promotions) and removed from it (demotions), and how fast right now
        promotions, demotions = raw.get('promotions'), raw.get('demotions')
        promo_bps = demo_bps = None
        if promotions is not None:
            if self.prev_migration:
                mdt = now - self.prev_migration[0]
                if mdt > 0:
                    self.promo_history.append((promotions - self.prev_migration[1]) * block_size / mdt)
                    self.demo_history.append((demotions - self.prev_migration[2]) * block_size / mdt)
                    promo_bps = sum(self.promo_history) / len(self.promo_history)
                    demo_bps = sum(self.demo_history) / len(self.demo_history)
            self.prev_migration = (now, promotions, demotions)

        return {
            'total_blocks': total_blocks,
            'used_blocks': used_blocks,
            'dirty_blocks': dirty_blocks,
            'cache_usage_pct': cache_usage_pct,
            'dirty_ratio_pct': dirty_ratio_pct,
            'hit_ratio_pct': hit_ratio_pct,
            'read_hit_ratio_pct': read_hit_ratio_pct,
            'write_hit_ratio_pct': write_hit_ratio_pct,
            'read_hits': read_hits,
            'read_misses': read_misses,
            'write_hits': write_hits,
            'write_misses': write_misses,
            'total_reads': total_reads,
            'total_writes': total_writes,
            'total_ops': total_ops,
            'block_size': block_size,
            'pool_size_bytes': pool_size_bytes,
            'promotions': promotions,
            'demotions': demotions,
            'promo_bps': promo_bps,
            'demo_bps': demo_bps,
            'cache_mode': raw['cache_mode'],
            'dirty_drain_bps': dirty_drain_bps,
            'dirty_eta_seconds': dirty_eta,
        }
    
    def read_meminfo(self):
        """Read the memory counters we care about (in kB) from /proc/meminfo"""
        wanted = ('MemTotal', 'MemAvailable', 'Dirty', 'Writeback')
        info = {}
        try:
            with open('/proc/meminfo') as f:
                for line in f:
                    key, _, rest = line.partition(':')
                    if key in wanted:
                        info[key] = int(rest.split()[0])
        except (OSError, ValueError, IndexError):
            return None
        return info if all(k in info for k in wanted) else None

    def read_dirty_limit_kb(self, mem_available_kb):
        """Dirty-data level where the kernel starts stalling writers (vm.dirty_bytes or dirty_ratio)"""
        def read(name):
            try:
                with open(f'/proc/sys/vm/{name}') as f:
                    return int(f.read().strip())
            except (OSError, ValueError):
                return 0
        limit_bytes = read('dirty_bytes')
        if limit_bytes:
            return limit_bytes // 1024
        return int(mem_available_kb * (read('dirty_ratio') or 20) / 100)

    def find_vg_disks(self):
        """Find the spinning disk (slow origin) and the fast cache disk in this volume group"""
        found = {'hdd': None, 'cache': None}
        try:
            result = subprocess.run(
                [*SUDO, 'pvs', '--noheadings', '-o', 'pv_name', '-S', f'vg_name={self.vg_name}'],
                capture_output=True, text=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return found
        for pv in result.stdout.split():
            name = os.path.basename(os.path.realpath(pv))
            sys_path = os.path.realpath(f'/sys/class/block/{name}')
            if os.path.exists(os.path.join(sys_path, 'partition')):
                name = os.path.basename(os.path.dirname(sys_path))  # partition -> whole disk
            try:
                with open(f'/sys/block/{name}/queue/rotational') as f:
                    role = 'hdd' if f.read().strip() == '1' else 'cache'
            except OSError:
                continue
            if found[role] is None:
                found[role] = name
        return found

    def read_nvme_temp(self, name):
        """NVMe composite temperature in C (readable without root), or None"""
        m = re.match(r'(nvme\d+)n\d+$', name or '')
        if not m:
            return None
        for path in glob.glob(f'/sys/class/nvme/{m.group(1)}/hwmon*/temp1_input'):
            try:
                with open(path) as f:
                    return int(f.read().strip()) / 1000
            except (OSError, ValueError):
                continue
        return None

    def read_disk_counters_many(self, names):
        """Cumulative I/O counters for several disks from one /proc/diskstats read"""
        wanted = {n for n in names if n}
        found = {}
        try:
            with open('/proc/diskstats') as f:
                for line in f:
                    p = line.split()
                    if len(p) >= 13 and p[2] in wanted:
                        found[p[2]] = {
                            'rd_ios': int(p[3]), 'rd_sectors': int(p[5]), 'rd_ms': int(p[6]),
                            'wr_ios': int(p[7]), 'wr_sectors': int(p[9]), 'wr_ms': int(p[10]),
                            'inflight': int(p[11]), 'io_ms': int(p[12]),
                        }
        except (OSError, ValueError):
            pass
        return found

    def ext4lazyinit_running(self):
        """Is the ext4lazyinit kernel thread alive? Re-checks the known pid each refresh and only
        rescans /proc every 10 seconds when it is not found."""
        pid = self.lazyinit_pid
        if pid:
            try:
                with open(f'/proc/{pid}/comm') as f:
                    if f.read().strip() == 'ext4lazyinit':
                        return True
            except OSError:
                pass
            self.lazyinit_pid = None
        now = time.monotonic()
        if now < self.lazyinit_next_scan:
            return False
        self.lazyinit_next_scan = now + 10
        try:
            names = os.listdir('/proc')
        except OSError:
            return False
        for name in names:
            if name.isdigit():
                try:
                    with open(f'/proc/{name}/comm') as f:
                        if f.read().strip() == 'ext4lazyinit':
                            self.lazyinit_pid = name
                            return True
                except OSError:
                    continue
        return False

    LAZYINIT_MIN_SPAN = 120   # seconds of history needed before quoting a speed

    def _lazyinit_refresh(self):
        """Count block groups whose inode table is zeroed (runs in a background thread)"""
        st = self.lazyinit
        try:
            out = subprocess.run(['dumpe2fs', f'/dev/{self.vg_name}/{self.lv_name}'],
                                 capture_output=True, text=True, timeout=180).stdout
            total = zeroed = 0
            for line in out.splitlines():
                if re.match(r'Group \d+:', line):
                    total += 1
                    if 'ITABLE_ZEROED' in line:
                        zeroed += 1
            if total:
                st['zeroed'], st['total'] = zeroed, total
                st['history'].append((time.monotonic(), zeroed))
        except (OSError, subprocess.SubprocessError):
            pass
        finally:
            st['busy'] = False

    def lazyinit_status(self):
        """Progress of ext4's background inode-table zeroing, or None when there is nothing to show"""
        st = self.lazyinit
        running = self.ext4lazyinit_running()
        if running:
            st['seen'] = True
        if not st['seen']:
            return None
        if not running:
            return {'state': 'finished'}
        if os.geteuid() != 0:
            return {'state': 'needs_root'}   # dumpe2fs must read the device
        now = time.monotonic()
        if not st['busy'] and now >= st['next']:
            st['busy'], st['next'] = True, now + 60
            threading.Thread(target=self._lazyinit_refresh, daemon=True).start()
        if st['zeroed'] is None:
            return {'state': 'checking'}
        info = {'state': 'running', 'zeroed': st['zeroed'], 'total': st['total'], 'rate_per_min': None,
                'eta_seconds': None, 'span_seconds': 0, 'age_seconds': time.monotonic() - st['history'][-1][0] if st['history'] else 0}
        hist = st['history']
        if len(hist) >= 2 and hist[-1][0] - hist[0][0] >= self.LAZYINIT_MIN_SPAN:
            per_sec = (hist[-1][1] - hist[0][1]) / (hist[-1][0] - hist[0][0])
            info['rate_per_min'] = per_sec * 60
            info['span_seconds'] = hist[-1][0] - hist[0][0]
            if per_sec > 0:
                info['eta_seconds'] = (st['total'] - st['zeroed']) / per_sec
        return info

    def disk_rates(self, cur, prev, dt):
        """Turn two cumulative counter snapshots into MB/s, latency and busy %"""
        rd = cur['rd_ios'] - prev['rd_ios']
        wr = cur['wr_ios'] - prev['wr_ios']
        return {
            'read_mbps': (cur['rd_sectors'] - prev['rd_sectors']) * 512 / dt / 1e6,
            'write_mbps': (cur['wr_sectors'] - prev['wr_sectors']) * 512 / dt / 1e6,
            'read_ms': (cur['rd_ms'] - prev['rd_ms']) / rd if rd > 0 else 0.0,
            'write_ms': (cur['wr_ms'] - prev['wr_ms']) / wr if wr > 0 else 0.0,
            'busy_pct': min(100.0, (cur['io_ms'] - prev['io_ms']) / (dt * 1000) * 100),
            'inflight': cur['inflight'],
        }

    def get_system_stats(self):
        """Dirty data waiting in RAM, how fast it drains, and how busy the HDD and cache drive are"""
        now = time.monotonic()
        mem = self.read_meminfo()
        if not mem:
            return None

        if not self.disk_checked:
            self.disk_checked = True
            self.disk_names = self.find_vg_disks()
        found = self.read_disk_counters_many(self.disk_names.values())
        counters = {role: found.get(name) for role, name in self.disk_names.items()}

        dirty = mem['Dirty']
        info = {
            'mem_total_kb': mem['MemTotal'],
            'dirty_kb': dirty,
            'writeback_kb': mem['Writeback'],
            'dirty_limit_kb': self.read_dirty_limit_kb(mem['MemAvailable']),
            'drain_kbps': None,   # positive = shrinking, negative = growing
            'eta_seconds': None,
            'disks': {role: {'name': name, 'rates': None, 'temp': self.read_nvme_temp(name)}
                      for role, name in self.disk_names.items()},
            'lazyinit': self.lazyinit_status(),
        }

        prev = self.prev_sample
        if prev:
            dt = now - prev['time']
            if dt > 0:
                drain = (prev['dirty_kb'] - dirty) / dt
                self.drain_history.append(drain)
                info['drain_kbps'] = sum(self.drain_history) / len(self.drain_history)
                if info['drain_kbps'] > 1024 and dirty > 0:  # draining faster than 1 MB/s
                    info['eta_seconds'] = dirty / info['drain_kbps']

        # Drive speeds: compare against the oldest snapshot inside the window (time-weighted average,
        # including latency), instead of only the last refresh, so lumpy I/O reads as a steady figure.
        for role, cur in counters.items():
            if not cur:
                continue
            snaps = self.disk_snaps[role]
            snaps.append((now, cur))
            while len(snaps) > 2 and now - snaps[1][0] >= DRIVE_RATE_WINDOW:
                snaps.popleft()
            t0, before = snaps[0]
            if now - t0 > 0:
                info['disks'][role]['rates'] = self.disk_rates(cur, before, now - t0)

        self.prev_sample = {'time': now, 'dirty_kb': dirty, 'counters': counters}
        return info

    def create_bar_graph(self, value, max_value=100, width=None, color='green'):
        """Create a horizontal bar graph"""
        if width is None:
            width = self.get_dynamic_widths()['bar_width']
            
        if max_value == 0:
            filled = 0
        else:
            filled = int((value / max_value) * width)
        
        bar = '█' * filled + '░' * (width - filled)
        color_code = self.colors.get(color, '')
        reset = self.colors['reset']
        
        return f"{color_code}{bar}{reset}"
    
    def clear_screen(self):
        """Clear the terminal screen"""
        pass  # frames are redrawn in place by run(); no `clear` process per refresh
    
    def format_size(self, blocks, block_size=None):
        """Format block count to human readable size"""
        if block_size is None:
            block_size = 4096  # Default block size
        bytes_size = blocks * block_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}PB"
    
    def format_bytes(self, bytes_size):
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}PB"
    
    def format_duration(self, seconds):
        """Format seconds as e.g. 1h05m, 12m30s or 45s"""
        seconds = int(seconds)
        if seconds >= 3600:
            return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"
        if seconds >= 60:
            return f"{seconds // 60}m{seconds % 60:02d}s"
        return f"{seconds}s"

    def print_system_section(self, sysinfo, widths):
        """Dirty data held in RAM (not yet written to disk) and HDD activity"""
        c = self.colors
        print(f"{c['bold']}Dirty Data (RAM) and Drives:{c['reset']} {c['dim']}(drive figures: {DRIVE_RATE_WINDOW:g} s average){c['reset']}")
        if not sysinfo:
            print("  Could not read /proc/meminfo")
            print()
            return

        dirty_b = sysinfo['dirty_kb'] * 1024
        wb_b = sysinfo['writeback_kb'] * 1024
        dirty_pct = min(100.0, sysinfo['dirty_kb'] / max(sysinfo['dirty_limit_kb'], 1) * 100)
        gb_kb = 1024 * 1024
        dirty_color = 'green' if sysinfo['dirty_kb'] < gb_kb else 'yellow' if sysinfo['dirty_kb'] < 4 * gb_kb else 'red'

        print(f"Dirty (RAM):  {c[dirty_color]}{self.format_bytes(dirty_b)}{c['reset']} waiting to be written"
              f"  |  {self.format_bytes(wb_b)} being written now")

        drain = sysinfo['drain_kbps']
        if drain is None:
            print("Drain rate:   measuring...")
        elif drain > 1024:
            eta = f"  ETA to clear: {self.format_duration(sysinfo['eta_seconds'])}" if sysinfo['eta_seconds'] else ""
            print(f"Drain rate:   {c['green']}{self.format_bytes(drain * 1024)}/s draining{c['reset']}{eta}")
        elif drain < -1024:
            print(f"Drain rate:   {c['red']}{self.format_bytes(-drain * 1024)}/s growing{c['reset']}")
        else:
            print("Drain rate:   steady")

        bar = self.create_bar_graph(dirty_pct, 100, None, dirty_color)
        print(f"Dirty RAM     [{bar}] {dirty_pct:.1f}% of {self.format_bytes(sysinfo['dirty_limit_kb'] * 1024)} limit")

        print()                       # blank line between RAM, NVMe and HDD to keep it readable
        self.print_disk_block('NVMe', sysinfo['disks']['cache'], slow=False)
        print()
        self.print_disk_block('HDD', sysinfo['disks']['hdd'], slow=True)
        self.print_lazyinit(sysinfo.get('lazyinit'))
        print()

    def print_lazyinit(self, li):
        """Progress of the one-time ext4 background setup after mkfs"""
        if not li:
            return
        print()                       # separate it from the HDD lines above
        c = self.colors
        head = "ext4 init:".ljust(14)
        if li['state'] == 'finished':
            print(f"{head}{c['green']}finished{c['reset']} (inode tables are fully zeroed)")
        elif li['state'] == 'needs_root':
            print(f"{head}running in the background (run with sudo to see progress)")
        elif li['state'] == 'checking':
            print(f"{head}running; reading progress...")
        else:
            zeroed, total = li['zeroed'], li['total']
            remaining = total - zeroed
            pct = zeroed / total * 100
            print(f"{head}[{self.create_bar_graph(pct, 100, None, 'cyan')}] {pct:.1f}% done")
            pad = ' ' * 14
            print(f"{pad}{zeroed:,} of {total:,} groups zeroed  |  {c['yellow']}{remaining:,} remaining ({100 - pct:.1f}%){c['reset']}")
            age = f"checked {int(li['age_seconds'])}s ago"
            if li['eta_seconds']:
                print(f"{pad}{li['rate_per_min']:,.0f} groups/min (avg {self.format_duration(li['span_seconds'])})"
                      f"  |  ETA {self.format_duration(li['eta_seconds'])}  |  {age}")
            elif li['rate_per_min'] is not None:
                print(f"{pad}no progress lately (job pauses while the disk is busy)  |  {age}")
            else:
                print(f"{pad}measuring speed...  |  {age}")

    def print_disk_block(self, label, entry, slow):
        """Two lines of throughput/latency plus a busy bar for one drive"""
        c = self.colors
        name = entry['name']
        head = f"{label} {name}:".ljust(14)
        if not name:
            print(f"{label}:".ljust(14) + "drive not found")
            return
        d = entry['rates']
        if not d:
            print(head + "measuring...")
            return
        busy_color = 'red' if d['busy_pct'] > 90 else 'yellow' if d['busy_pct'] > 60 else 'green'
        lat = max(d['read_ms'], d['write_ms'])
        red_ms, yellow_ms = (100, 30) if slow else (20, 5)
        lat_color = 'red' if lat > red_ms else 'yellow' if lat > yellow_ms else 'green'
        print(f"{head}write {d['write_mbps']:.1f} MB/s  read {d['read_mbps']:.1f} MB/s"
              f"  |  queue {d['inflight']}")
        line2 = (f"{' ' * 14}busy {c[busy_color]}{d['busy_pct']:.0f}%{c['reset']}"
                 f"  |  latency write {c[lat_color]}{d['write_ms']:.0f} ms{c['reset']}"
                 f"  read {c[lat_color]}{d['read_ms']:.0f} ms{c['reset']}")
        temp = entry['temp']
        if temp is not None:
            temp_color = 'red' if temp >= 70 else 'yellow' if temp >= 60 else 'green'
            line2 += f"  |  temp {c[temp_color]}{temp:.0f}\u00b0C{c['reset']}"
        print(line2)
        busy_bar = self.create_bar_graph(d['busy_pct'], 100, None, busy_color)
        print(f"{label + ' Busy':<14}[{busy_bar}] {d['busy_pct']:.0f}%")

    ANSI_RE = re.compile(r'\033\[[0-9;]*m')

    def vlen(self, s):
        """Visible length of a string that contains color codes"""
        return len(self.ANSI_RE.sub('', s))

    def print_wrapped(self, text, indent=2, first_indent=None):
        """Print text wrapped at MAX_WIDTH; color codes do not count toward the width"""
        words = text.split(' ')
        lead = ' ' * (indent if first_indent is None else first_indent)
        line, length = lead, len(lead)
        for word in words:
            wl = self.vlen(word)
            if length + wl + (1 if line.strip() else 0) > MAX_WIDTH and line.strip():
                print(line)
                line, length = ' ' * indent, indent
            if line.strip():
                line += ' '
                length += 1
            line += word
            length += wl
        print(line)

    def pad(self, s, width):
        return s + ' ' * max(0, width - self.vlen(s))

    def short_bytes(self, n):
        """Compact size for the narrow diagram boxes: 345MB, 8.8GB"""
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if n < 1024 or unit == 'TB':
                return f"{n:.0f}{unit}" if (n >= 100 or unit == 'B') else f"{n:.1f}{unit}"
            n /= 1024

    def rate_pair(self, read_mbps, write_mbps):
        """'R1.4 W26.5 MB/s' that always fits a drive box, switching to GB/s for fast NVMe drives"""
        top = max(read_mbps, write_mbps)
        if top >= 1000:
            return f"R{read_mbps / 1000:.1f} W{write_mbps / 1000:.1f} GB/s"
        digits = 0 if top >= 100 else 1
        return f"R{read_mbps:.{digits}f} W{write_mbps:.{digits}f} MB/s"

    def pressure_color(self, pct):
        return 'green' if pct < 50 else 'yellow' if pct < 85 else 'red'

    def mini_meter(self, pct, cells=7):
        filled = max(0, min(cells, int(round(pct / 100 * cells))))
        return '█' * filled + '░' * (cells - filled)

    def make_box(self, rows, inner, color):
        """Draw a box around text rows; width is inner + 4"""
        edge, reset = self.colors[color], self.colors['reset']
        top = f"{edge}┌{'─' * (inner + 2)}┐{reset}"
        bottom = f"{edge}└{'─' * (inner + 2)}┘{reset}"
        def clip(row):
            if self.vlen(row) <= inner:
                return row
            return self.ANSI_RE.sub('', row)[:inner - 1] + '…'      # too long: drop colors, keep the border intact
        body = [f"{edge}│{reset} {self.pad(clip(row), inner)} {edge}│{reset}" for row in rows]
        return [top, *body, bottom]

    def pipeline_pressures(self, stats, sysinfo):
        """How loaded each stage is, 0-100"""
        def busy(role):
            rates = sysinfo['disks'][role]['rates']
            return rates['busy_pct'] if rates else 0.0
        limit = max(sysinfo['dirty_limit_kb'], 1)
        return {
            'ram': min(100.0, sysinfo['dirty_kb'] / limit * 100),                  # vs the kernel stall limit
            'lvm': min(100.0, stats['dirty_ratio_pct'] * 4) if stats else 0.0,     # dirty share of the cache
            'nvme': busy('cache'),
            'hdd': busy('hdd'),
        }

    def find_bottleneck(self, pr):
        """The most loaded device. If RAM is full only because a device is slow, blame the device."""
        downstream = {k: pr[k] for k in ('hdd', 'nvme', 'lvm')}   # HDD wins ties
        worst = max(downstream, key=downstream.get)
        if downstream[worst] >= 85:
            return worst
        return 'ram' if pr['ram'] >= 85 else None

    def print_pipeline(self, stats, sysinfo, widths):
        """ASCII picture of the write path with the live bottleneck highlighted"""
        c = self.colors
        pr = self.pipeline_pressures(stats, sysinfo)
        # Writeback is holding data but nothing is flushing it, and no device is busy: dm-cache only
        # writes dirty blocks back when the volume has been quiet for a moment.
        held = stats['dirty_blocks'] * stats['block_size'] if stats and stats['cache_mode'] == 'writeback' else 0
        stuck = (held >= 1024 ** 3 and stats['dirty_drain_bps'] is not None and stats['dirty_drain_bps'] <= 65536
                 and pr['hdd'] < 60 and pr['nvme'] < 60 and pr['ram'] < 85)
        if stuck:
            pr['lvm'] = max(pr['lvm'], 60)       # show the LVM box in yellow
        worst = self.find_bottleneck(pr)
        hdd, nvme = sysinfo['disks']['hdd'], sysinfo['disks']['cache']
        col = lambda key: self.pressure_color(pr[key])
        bold, reset = c['bold'], c['reset']

        N = 5   # text lines inside every box, so all the boxes line up

        def ms_text(ms):
            return f"{ms:.0f}ms" if ms < 1000 else f"{ms / 1000:.1f}s" if ms < 10000 else ">10s"

        # --- text for each stage ---
        dirty_b = sysinfo['dirty_kb'] * 1024
        ram = [f"{bold}RAM CACHE{reset}", f"{self.short_bytes(dirty_b)} dirty",
               f"{c[col('ram')]}{self.mini_meter(pr['ram'], 10)}{reset} {pr['ram']:3.0f}%",
               f"{self.short_bytes(sysinfo['dirty_limit_kb'] * 1024)} limit"]

        drain = sysinfo['drain_kbps']
        if drain is None:
            flow, eta = "measuring...", ""
        elif drain > 1024:
            flow = f"{self.format_bytes(drain * 1024)}/s ↓"
            eta = f"ETA {self.format_duration(sysinfo['eta_seconds'])}" if sysinfo['eta_seconds'] else ""
        elif drain < -1024:
            flow, eta = f"+{self.format_bytes(-drain * 1024)}/s ↑", "growing"
        else:
            flow, eta = "steady", ""
        kernel = [f"{bold}KERNEL FLUSH{reset}", flow, eta, f"{self.short_bytes(sysinfo['writeback_kb'] * 1024)} writing"]

        if stats:
            mode, blocks = stats['cache_mode'], stats['dirty_blocks']
            if blocks:
                line3 = f"{self.short_bytes(blocks * stats['block_size'])} dirty"
                d = stats['dirty_drain_bps']      # how fast dirty LVM blocks are flushed to the HDD
                if d is None:
                    line4, line5 = "measuring...", ""
                elif d > 65536:
                    line4 = f"{c['green']}{self.format_bytes(d)}/s ↓{reset}"
                    eta_s = stats['dirty_eta_seconds']
                    line5 = f"ETA {self.format_duration(eta_s)}" if eta_s is not None else ""
                elif d < -65536:
                    line4, line5 = f"{c['red']}+{self.format_bytes(-d)}/s ↑{reset}", "growing"
                else:
                    line4, line5 = "steady", ""
            else:
                line3 = f"{stats['cache_usage_pct']:.0f}% full"
                line4, line5 = ("clean", "") if mode == 'writeback' else ("", "")
            lvm = [f"{bold}LVM CACHE{reset}", mode, line3, line4, line5]
        else:
            lvm = [f"{bold}LVM CACHE{reset}", "unavailable"]

        def drive_rows(label, entry, with_temp):
            name, d = entry['name'], entry['rates']
            if not name:
                return [f"{bold}{label}{reset}", "not found"]
            if not d:
                return [f"{bold}{label} {name}{reset}", "measuring..."]
            temp = f" {entry['temp']:.0f}°C" if with_temp and entry['temp'] is not None else ""
            return [f"{bold}{label} {name}{reset}", f"{d['busy_pct']:.0f}% busy{temp}",
                    self.rate_pair(d['read_mbps'], d['write_mbps']),
                    f"latency w{ms_text(d['write_ms'])} r{ms_text(d['read_ms'])}",
                    f"queue {d['inflight']}"]

        def fit(rows):
            return (rows + [''] * N)[:N]

        print(f"{bold}I/O Pipeline (writes flow left to right):{reset} {c['dim']}(drive figures: {DRIVE_RATE_WINDOW:g} s average){reset}")
        boxes = {
            'ram': self.make_box(fit(ram), PIPE_STAGE_INNER, col('ram')),
            'ker': self.make_box(fit(kernel), PIPE_STAGE_INNER, 'cyan'),
            'lvm': self.make_box(fit(lvm), PIPE_STAGE_INNER, col('lvm')),
            'nvme': self.make_box(fit(drive_rows('NVMe', nvme, True)), PIPE_DRIVE_INNER, col('nvme')),
            'hdd': self.make_box(fit(drive_rows('HDD', hdd, False)), PIPE_DRIVE_INNER, col('hdd')),
        }

        # --- geometry: two drive boxes stacked on the right, the three stages centred beside them ---
        H = N + 2                          # box height
        total = 2 * H + 1                  # rows in the whole picture
        top = (total - H) // 2             # first row of the stage boxes
        mid = top + 1 + N // 2             # the row the arrows run along
        nvme_arm = 1 + N // 2              # row where the branch enters the NVMe box
        hdd_arm = H + 1 + 1 + N // 2       # row where the branch enters the HDD box
        cy = c['cyan']
        stage_w, drive_w = PIPE_STAGE_INNER + 4, PIPE_DRIVE_INNER + 4
        for r in range(total):
            def stage(box):
                i = r - top
                return box[i] if 0 <= i < H else ' ' * stage_w
            if r < H:
                drive = boxes['nvme'][r]
            elif r == H:
                drive = ' ' * drive_w
            else:
                drive = boxes['hdd'][r - H - 1]
            gap = f"{cy}{'─' * (PIPE_GAP - 1)}▶{reset}" if r == mid else ' ' * PIPE_GAP
            if r == nvme_arm:
                arm = "   ┌──▶"
            elif r == hdd_arm:
                arm = "   └──▶"
            elif r == mid:
                arm = "───┤   "
            elif nvme_arm < r < hdd_arm:
                arm = "   │   "
            else:
                arm = "       "
            print(' ' + stage(boxes['ram']) + gap + stage(boxes['ker']) + gap + stage(boxes['lvm']) + f"{cy}{arm}{reset}" + drive)

        # --- the verdict ---
        lat = 0.0
        if hdd['rates']:
            lat = max(hdd['rates']['read_ms'], hdd['rates']['write_ms'])
        if worst == 'hdd':
            rd, wr = hdd['rates']['read_mbps'], hdd['rates']['write_mbps']
            backed_up = pr['ram'] >= 10 or sysinfo['dirty_kb'] >= 256 * 1024
            held = stats['dirty_blocks'] * stats['block_size'] if stats and stats['cache_mode'] == 'writeback' else 0
            head = (f"{c['red']}Bottleneck: HDD {hdd['name']}{reset} ({pr['hdd']:.0f}% busy, {lat:.0f} ms latency, "
                    f"reading {rd:.1f} / writing {wr:.1f} MB/s).")
            if backed_up:
                tail = "Everything to its left is waiting on it."
            elif held >= 256 * 1024 * 1024:
                tail = (f"Nothing is queued in RAM, but writeback is holding {self.short_bytes(held)} "
                        f"that is not on the HDD yet.")
            else:
                tail = "Nothing upstream is backed up; it is busy with its own reads and background work."
            msg = f"{head} {tail}"
        elif worst == 'nvme':
            msg = f"{c['red']}Bottleneck: NVMe cache drive{reset} ({pr['nvme']:.0f}% busy)."
        elif worst == 'lvm':
            msg = (f"{c['red']}Bottleneck: LVM cache{reset} ({stats['dirty_ratio_pct']:.1f}% of the cache is dirty; "
                   f"flushing to the HDD is lagging).")
        elif worst == 'ram':
            msg = (f"{c['red']}Bottleneck: RAM{reset} (dirty data is at {pr['ram']:.0f}% of the kernel stall limit; "
                   f"writers will be paused).")
        elif stuck:
            msg = (f"{c['yellow']}Stalled:{reset} writeback is holding {self.short_bytes(held)} that is not on the HDD, "
                   f"but nothing is flushing it and the HDD is only {pr['hdd']:.0f}% busy. dm-cache writes dirty blocks "
                   f"back only when the volume has been quiet for a moment, and I/O to {self.vg_name}/{self.lv_name} never "
                   f"pauses (often ext4lazyinit or the journal). To let it flush, stop whatever uses the volume "
                   f"(close programs, unmount it); a backlog then drains at disk speed.")
        elif max(pr.values()) < 10 and sysinfo['dirty_kb'] < 100 * 1024:
            msg = f"{c['green']}Idle:{reset} nothing significant is moving through the pipeline."
        else:
            msg = f"{c['green']}No bottleneck:{reset} every stage is keeping up."
        self.print_wrapped(msg, indent=1)
        print()

    def display_stats(self, stats, sysinfo=None):
        """Display current statistics and bars"""
        if not stats:
            self.clear_screen()
            print(f"{self.colors['red']}Error: Could not retrieve LVM cache statistics{self.colors['reset']}")
            print("Make sure the volume group and logical volume exist and you have sudo privileges.")
            print()
            self.print_system_section(sysinfo, self.get_dynamic_widths())
            return

        self.clear_screen()
        
        # Get dynamic widths for this refresh
        widths = self.get_dynamic_widths()
        
        # Header - adjust based on terminal width
        header_text = f"cachetop - {self.vg_name}/{self.lv_name}"
        separator = "=" * min(len(header_text) + 10, widths['terminal_width'])
        
        print(f"{self.colors['bold']}{self.colors['cyan']}{header_text}{self.colors['reset']}")
        print(separator)
        print()
        
        # pipeline picture, then RAM/drives, then the LVM cache
        if sysinfo:
            self.print_pipeline(stats, sysinfo, widths)
        self.print_system_section(sysinfo, widths)

        # Current stats
        print(f"{self.colors['bold']}LVM Cache:{self.colors['reset']}")
        
        # Show actual cache pool size
        cache_pool_size = self.format_bytes(stats['pool_size_bytes'])
        used_cache_size = self.format_size(stats['used_blocks'], stats['block_size'])
        dirty_cache_size = self.format_size(stats['dirty_blocks'], stats['block_size'])
        
        mode = stats['cache_mode']
        mode_color = 'green' if mode == 'writethrough' else 'yellow'
        mode_note = "" if mode == 'writethrough' else "  (dirty LVM blocks exist only on the cache until flushed)"
        print(f"Cache Mode:   {self.colors[mode_color]}{mode}{self.colors['reset']}{mode_note}")
        print(f"Cache Pool:   {cache_pool_size} total")
        print(f"Cache Usage:  {stats['cache_usage_pct']:.1f}% ({used_cache_size} used)")
        if stats['promotions'] is None:
            print("Copied in:    n/a (needs dmsetup)")
        else:
            bs = stats['block_size']
            print(f"Copied in:    {self.format_bytes(stats['promotions'] * bs)} ({stats['promotions']:,} blocks, HDD to cache)"
                  f"  |  now {self.format_bytes(stats['promo_bps'] or 0)}/s")
            print(f"Evicted:      {self.format_bytes(stats['demotions'] * bs)} ({stats['demotions']:,} blocks, dropped from cache)"
                  f"  |  now {self.format_bytes(stats['demo_bps'] or 0)}/s")
        # Dirty data only exists in writeback mode (or as leftovers right after leaving it)
        show_dirty = stats['cache_mode'] == 'writeback' or stats['dirty_blocks'] > 0
        if show_dirty:
            print(f"Dirty Blocks: {stats['dirty_ratio_pct']:.1f}% ({dirty_cache_size} dirty on the LVM cache)")
            drain = stats['dirty_drain_bps']
            if stats['dirty_blocks'] == 0:
                print("Flush:        nothing pending")
            elif drain is None:
                print("Flush:        measuring...")
            elif drain > 65536:
                eta = f"  ETA to clear: {self.format_duration(stats['dirty_eta_seconds'])}" if stats['dirty_eta_seconds'] is not None else ""
                print(f"Flush:        {self.colors['green']}{self.format_bytes(drain)}/s flushing{self.colors['reset']}{eta}")
            elif drain < -65536:
                print(f"Flush:        {self.colors['red']}{self.format_bytes(-drain)}/s growing{self.colors['reset']}")
            else:
                print("Flush:        steady (no net flushing)")
        print(f"Hit Ratio:    {stats['hit_ratio_pct']:.1f}% ({stats['total_ops']:,} operations)")
        print(f"Read Hits:    {stats['read_hit_ratio_pct']:.1f}% ({stats['read_hits']:,} hits, {stats['read_misses']:,} misses)")
        print(f"Write Hits:   {stats['write_hit_ratio_pct']:.1f}% ({stats['write_hits']:,} hits, {stats['write_misses']:,} misses)")
        print()
        
        # Bar graphs
        print(f"{self.colors['bold']}Real-time Status:{self.colors['reset']}")
        
        usage_bar = self.create_bar_graph(stats['cache_usage_pct'], 100, None, 'cyan')
        print(f"Cache Usage   [{usage_bar}] {stats['cache_usage_pct']:.1f}%")

        # Dirty blocks bar (hidden when there is nothing to show, see show_dirty above)
        if show_dirty:
            dirty_bar = self.create_bar_graph(stats['dirty_ratio_pct'], 100, None, 'blue')
            print(f"Dirty Blocks  [{dirty_bar}] {stats['dirty_ratio_pct']:.1f}%")
        
        # Hit ratio bar
        hit_color = 'green' if stats['hit_ratio_pct'] > 80 else 'yellow' if stats['hit_ratio_pct'] > 60 else 'red'
        hit_bar = self.create_bar_graph(stats['hit_ratio_pct'], 100, None, hit_color)
        print(f"Hit Ratio     [{hit_bar}] {stats['hit_ratio_pct']:.1f}%")
        
        # Read hit ratio bar
        read_hit_color = 'green' if stats['read_hit_ratio_pct'] > 80 else 'yellow' if stats['read_hit_ratio_pct'] > 60 else 'red'
        read_hit_bar = self.create_bar_graph(stats['read_hit_ratio_pct'], 100, None, read_hit_color)
        print(f"Read Hits     [{read_hit_bar}] {stats['read_hit_ratio_pct']:.1f}%")
        
        # Write hit ratio bar
        write_hit_color = 'green' if stats['write_hit_ratio_pct'] > 80 else 'yellow' if stats['write_hit_ratio_pct'] > 60 else 'red'
        write_hit_bar = self.create_bar_graph(stats['write_hit_ratio_pct'], 100, None, write_hit_color)
        print(f"Write Hits    [{write_hit_bar}] {stats['write_hit_ratio_pct']:.1f}%")
        print()
        

        # Add terminal size info at bottom
        print(f"{self.colors['dim']}Refresh {self.refresh_interval:g}s (+ faster, - slower) | q to quit{self.colors['reset']}")
    
    def wait_for_key(self, timeout, interactive):
        """Sleep up to `timeout` seconds; return a key if one was pressed"""
        if not interactive:
            time.sleep(max(timeout, 0))
            return None
        ready, _, _ = select.select([sys.stdin], [], [], max(timeout, 0))
        if ready:
            return os.read(sys.stdin.fileno(), 1).decode(errors='ignore')
        return None

    def set_refresh_interval(self, seconds):
        """Set the refresh rate (limited to the allowed range) and resize the ~10 s averaging windows to match"""
        self.refresh_interval = min(max(seconds, REFRESH_STEPS[0]), REFRESH_STEPS[-1])
        window = max(3, int(round(10 / self.refresh_interval)))
        for name in ('drain_history', 'cache_drain_history', 'promo_history', 'demo_history'):
            setattr(self, name, deque(getattr(self, name), maxlen=window))

    def step_refresh(self, faster):
        """Move to the next preset refresh rate; stays where it is at either end"""
        cur = self.refresh_interval
        if faster:
            options = [s for s in REFRESH_STEPS if s < cur - 1e-9]
            target = options[-1] if options else cur
        else:
            options = [s for s in REFRESH_STEPS if s > cur + 1e-9]
            target = options[0] if options else cur
        self.set_refresh_interval(target)

    def run(self, refresh_interval=1.0):
        """Main loop: draws each frame with a single write (no flicker) at a steady rate"""
        self.set_refresh_interval(refresh_interval)
        out = sys.stdout
        interactive = sys.stdin.isatty() and out.isatty()
        old_term = None
        if interactive:
            fd = sys.stdin.fileno()
            old_term = termios.tcgetattr(fd)
            tty.setcbreak(fd)                      # read single keys, no Enter needed
            out.write('\033[?1049h\033[?25l')      # alternate screen, hide cursor
            out.flush()
        try:
            self.get_system_stats()                # prime the rate counters
            time.sleep(min(self.refresh_interval, 0.5))
            next_tick = time.monotonic()
            while True:
                stats = self.get_lvm_cache_stats()
                sysinfo = self.get_system_stats()
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    self.display_stats(stats, sysinfo)
                out.write('\033[H' + buf.getvalue().replace('\n', '\033[K\n') + '\033[J')
                out.flush()

                next_tick += self.refresh_interval
                if next_tick < time.monotonic():   # fell behind; do not try to catch up
                    next_tick = time.monotonic()
                while True:
                    remaining = next_tick - time.monotonic()
                    if remaining <= 0:
                        break
                    key = self.wait_for_key(remaining, interactive)
                    if key in ('q', 'Q'):
                        return
                    if key in ('+', '='):
                        self.step_refresh(faster=True)
                        next_tick = time.monotonic()
                    elif key in ('-', '_'):
                        self.step_refresh(faster=False)
                        next_tick = time.monotonic()
        except KeyboardInterrupt:
            pass
        finally:
            if interactive:
                out.write('\033[?25h\033[?1049l')
                out.flush()
                termios.tcsetattr(fd, termios.TCSADRAIN, old_term)
            print("cachetop stopped.")

def detect_cache_volumes():
    """Detect available LVM cache volumes"""
    try:
        # Find all logical volumes with cache
        cmd = [*SUDO, 'lvs', '--noheadings', '--nosuffix', '-o', 'vg_name,lv_name,cache_policy', '--separator', '|']
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        cache_volumes = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3 and parts[2] and parts[2] != '':  # Has cache policy
                    vg_name = parts[0]
                    lv_name = parts[1]
                    cache_volumes.append((vg_name, lv_name))
        
        return cache_volumes
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

def get_key():
    """Get a single keypress from stdin"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        # Handle arrow keys
        if ch == '\x1b':  # ESC sequence
            ch += sys.stdin.read(2)
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def interactive_volume_selection(cache_volumes):
    """Interactive menu to select cache volume"""
    if not cache_volumes:
        print("No LVM cache volumes detected.")
        return None, None
    
    print("\n" + "=" * 60)
    print("cachetop - LVM Cache Volume Selection")
    print("=" * 60)
    print("Use ↑/↓ arrow keys to navigate, Enter to select, Ctrl+C to exit\n")
    
    selected = 0
    
    while True:
        # Clear previous menu (move cursor up and clear lines)
        if selected > 0 or True:  # Always clear on first display too
            print(f"\033[{len(cache_volumes) + 2}A", end="")  # Move cursor up
            print("\033[J", end="")  # Clear from cursor to end of screen
        
        # Display menu
        for i, (vg, lv) in enumerate(cache_volumes):
            if i == selected:
                print(f"  → \033[92m{vg}/{lv}\033[0m")  # Green highlight
            else:
                print(f"    {vg}/{lv}")
        
        print(f"\nSelected: \033[93m{cache_volumes[selected][0]}/{cache_volumes[selected][1]}\033[0m")
        
        # Get user input
        try:
            key = get_key()
            
            if key == '\x1b[A':  # Up arrow
                selected = (selected - 1) % len(cache_volumes)
            elif key == '\x1b[B':  # Down arrow
                selected = (selected + 1) % len(cache_volumes)
            elif key == '\r' or key == '\n':  # Enter
                vg_name, lv_name = cache_volumes[selected]
                print(f"\n\033[96mSelected: {vg_name}/{lv_name}\033[0m")
                print("Starting monitor...\n")
                return vg_name, lv_name
            elif key == '\x03':  # Ctrl+C
                print("\n\033[91mSelection cancelled.\033[0m")
                sys.exit(0)
                
        except KeyboardInterrupt:
            print("\n\033[91mSelection cancelled.\033[0m")
            sys.exit(0)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='cachetop - Real-time LVM cache monitor')
    parser.add_argument('--version', action='version', version='cachetop 2025.07')
    parser.add_argument('--vg', help='Volume group name')
    parser.add_argument('--lv', help='Logical volume name')
    parser.add_argument('--interval', type=float, default=1.0, help='Refresh interval in seconds, 0.25 to 10 (default: 1)')
    parser.add_argument('--pick', action='store_true', help='Force interactive volume selection even if auto-detection works')
    
    args = parser.parse_args()
    
    vg_name = args.vg
    lv_name = args.lv
    
    monitor = None
    if vg_name and lv_name and not args.pick:
        pass                                       # explicit volume: no detection needed
    elif not args.pick and not vg_name and not lv_name:
        # Fast path: try the default volume with one quick query before scanning LVM
        monitor = LVMCacheMonitor()
        if monitor.get_lvm_cache_stats():
            vg_name, lv_name = monitor.vg_name, monitor.lv_name
        else:
            monitor = None

    if not (vg_name and lv_name):
        print("\033[96mDetecting LVM cache volumes...\033[0m")
        cache_volumes = detect_cache_volumes()

        if not cache_volumes:
            print("\033[91mNo LVM cache volumes found.\033[0m")
            print("Make sure you have LVM cache configured and proper sudo privileges.")
            sys.exit(1)
        elif len(cache_volumes) == 1 and not args.pick:
            vg_name, lv_name = cache_volumes[0]
        else:
            if args.pick:
                print("Interactive selection requested with --pick flag")
            else:
                print(f"Found {len(cache_volumes)} cache volumes")
            vg_name, lv_name = interactive_volume_selection(cache_volumes)

            if not vg_name or not lv_name:
                print("\033[91mNo volume selected.\033[0m")
                sys.exit(1)

    if monitor is None:
        monitor = LVMCacheMonitor(vg_name, lv_name)
    # The first stats read doubles as the "is this a cache volume?" check
    if monitor.get_lvm_cache_stats() is None:
        print(f"\033[91mError: cannot read cache stats for {vg_name}/{lv_name}. "
              f"Check the names, that it has a cache, and sudo permissions.\033[0m")
        sys.exit(1)
    monitor.run(args.interval)

if __name__ == "__main__":
    main()
