# cachetop

A real-time terminal monitor for LVM cache (dm-cache) with an htop-style display. It shows how the cache is performing **and where your writes are actually waiting**: in RAM, in the kernel, in the LVM cache, on the cache drive, or on the slow disk behind it.

## Features

- 🧭 **I/O pipeline diagram** — RAM cache → kernel flush → LVM cache → cache drive / slow disk, with each stage colored by load and a plain-language **bottleneck verdict**
- 🧠 **Dirty data in RAM** — how much is waiting to be written, how fast it drains, an ETA, and how close it is to the kernel's stall limit
- 💽 **Both drives side by side** — throughput, latency, queue depth, busy % (and temperature for the NVMe), averaged over 5 seconds so lumpy I/O reads smoothly
- 🗄️ **Real LVM cache counters** — blocks copied into the cache (promotions) and evicted (demotions) with live rates, plus exact hit/miss counts
- ⏱️ **Writeback flush ETA** — speed and time-to-clear for dirty cache blocks, in the pipeline and in the LVM section
- 🛠️ **ext4 background init progress** — percent done, groups remaining, speed and ETA while `ext4lazyinit` zeroes a new filesystem's inode tables
- 📊 Color-coded percentage bars (cache usage, dirty blocks, hit ratios)
- ⚡ Light on the system: one `dmsetup status` query per refresh, flicker-free redraw, adjustable refresh rate
- 🔍 Automatic LVM cache volume detection, with an interactive picker when there are several
- ⌨️ `+` / `-` change the refresh rate while running, `q` quits

## Sample Output

The layout is a fixed 100 columns wide (the terminal must be at least that wide).

```
cachetop - vg_games/games
===================================

I/O Pipeline (writes flow left to right): (drive figures: 5 s average)
                                                                           ┌──────────────────────┐
                                                                           │ NVMe nvme0n1         │
                                                                           │ 8% busy 51°C         │
                                                                       ┌──▶│ R0 W160 MB/s         │
 ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │   │ latency w3ms r0ms    │
 │ RAM CACHE       │     │ KERNEL FLUSH    │     │ LVM CACHE       │   │   │ queue 1              │
 │ 8.1GB dirty     │     │ 16.6MB/s ↓      │     │ writeback       │   │   └──────────────────────┘
 │ ████░░░░░░  37% │────▶│ ETA 8m18s       │────▶│ 7.5GB dirty     │───┤
 │ 21.7GB limit    │     │ 56.0MB writing  │     │ 3.6MB/s ↓       │   │   ┌──────────────────────┐
 │                 │     │                 │     │ ETA 35m33s      │   │   │ HDD sda              │
 └─────────────────┘     └─────────────────┘     └─────────────────┘   │   │ 96% busy             │
                                                                       └──▶│ R2.1 W38.4 MB/s      │
                                                                           │ latency w142ms r15ms │
                                                                           │ queue 12             │
                                                                           └──────────────────────┘
 Bottleneck: HDD sda (96% busy, 142 ms latency, reading 2.1 / writing 38.4 MB/s). Everything to its
 left is waiting on it.

Dirty Data (RAM) and Drives: (drive figures: 5 s average)
Dirty (RAM):  8.1GB waiting to be written  |  56.0MB being written now
Drain rate:   16.6MB/s draining  ETA to clear: 8m18s
Dirty RAM     [██████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 37.3% of 21.7GB limit

NVMe nvme0n1: write 160.3 MB/s  read 0.2 MB/s  |  queue 1
              busy 8%  |  latency write 3 ms  read 0 ms  |  temp 51°C
NVMe Busy     [████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 8%

HDD sda:      write 38.4 MB/s  read 2.1 MB/s  |  queue 12
              busy 96%  |  latency write 142 ms  read 15 ms
HDD Busy      [█████████████████████████████████████████████████████████░░░] 96%

ext4 init:    [███████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 19.6% done
              11,704 of 59,617 groups zeroed  |  47,913 remaining (80.4%)
              85 groups/min (avg 30m00s)  |  ETA 9h25m  |  checked 22s ago

LVM Cache:
Cache Mode:   writeback  (dirty LVM blocks exist only on the cache until flushed)
Cache Pool:   930.9GB total
Cache Usage:  18.4% (170.9GB used)
Copied in:    23.8GB (24,373 blocks, HDD to cache)  |  now 14.0MB/s
Evicted:      40.0MB (40 blocks, dropped from cache)  |  now 0.0B/s
Dirty Blocks: 0.8% (7.5GB dirty on the LVM cache)
Flush:        3.6MB/s flushing  ETA to clear: 35m33s
Hit Ratio:    40.3% (1,368,838 operations)
Read Hits:    93.9% (392,163 hits, 25,675 misses)
Write Hits:   16.7% (159,015 hits, 791,985 misses)

Real-time Status:
Cache Usage   [███████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 18.4%
Dirty Blocks  [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0.8%
Hit Ratio     [████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 40.3%
Read Hits     [████████████████████████████████████████████████████████░░░░] 93.9%
Write Hits    [██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 16.7%

Refresh 1s (+ faster, - slower) | q to quit
```

*(Sample numbers; colors are not shown here. Stage boxes and bars turn green, yellow or red as load rises.)*

## Installation

### Binary Installation (Recommended)

**Quick install:**
```bash
# Download and run install script
curl -sSL https://raw.githubusercontent.com/Throdne/cachetop/main/install.sh | bash
```

**Manual binary install:**
```bash
# Download latest binary
wget https://github.com/Throdne/cachetop/releases/latest/download/cachetop-linux-x64
chmod +x cachetop-linux-x64
sudo mv cachetop-linux-x64 /usr/local/bin/cachetop
```

### From Source

```bash
# Clone repository
git clone https://github.com/Throdne/cachetop.git
cd cachetop

# Build binary
make binary

# Install system-wide
make install-binary
```

### Via pip (if available)

```bash
pip install cachetop
```

## Quick Start

Run it **as root** (`sudo`). Reading the cache counters and, for the ext4 progress line, the filesystem needs root.

```bash
# Auto-detect and monitor the LVM cache (default volume vg_games/games is tried first)
sudo cachetop

# Show help
cachetop --help

# Monitor a specific volume
sudo cachetop --vg my_vg --lv my_lv
```

**From source:**
```bash
# Basic usage with auto-detection
sudo python3 cachetop.py

# Refresh twice a second
sudo python3 cachetop.py --interval 0.5

# Force the interactive selection menu
sudo python3 cachetop.py --pick

# Monitor a specific volume (skip auto-detection)
sudo python3 cachetop.py --vg vg_games --lv games
```

While it is running: **`+`** refreshes faster, **`-`** slower, **`q`** (or Ctrl+C) quits.

## Requirements

- Python 3.7+
- LVM2 with dm-cache support (`dmsetup`; `lvs` and `pvs` are used for fallback and drive detection)
- Root privileges (run with `sudo`)
- A terminal at least **100 columns** wide with Unicode and ANSI color support
- Optional: `dumpe2fs` (e2fsprogs) for the ext4 initialization progress line

## Understanding the Display

### I/O Pipeline

```
RAM CACHE ──▶ KERNEL FLUSH ──▶ LVM CACHE ──┬──▶ NVMe (cache drive)
                                           └──▶ HDD  (slow origin disk)
```

Writes travel left to right. Each box shows what that stage is doing right now:

| Stage | What it shows |
|---|---|
| **RAM cache** | Dirty data waiting in the kernel page cache, a meter of how close it is to the stall limit, and the limit itself |
| **Kernel flush** | How fast the RAM backlog is draining (↓) or growing (↑), an ETA, and how much is being written this moment |
| **LVM cache** | The cache mode and either how full the cache is or how much dirty data it holds. In writeback mode with dirty blocks it also shows the flush speed and ETA |
| **NVMe / HDD** | Busy %, read/write throughput, latency, queue depth (and temperature for NVMe) |

Box borders are **green** below 50% load, **yellow** from 50%, and **red** from 85%.

The **Bottleneck** line names the most loaded device and says whether anything is actually waiting on it. If RAM is full only because a device is slow, it blames the device. It will also say when the disk is simply busy with its own reads, or when writeback is holding data that is not on the slow disk yet.

### Dirty Data (RAM) and Drives

- **Dirty (RAM)** — data that applications have written but the kernel has not flushed yet, and how much is being written right now.
- **Drain rate / ETA** — the change in dirty data, averaged over about 10 seconds. `ETA = dirty data ÷ drain rate`. It is the *net* rate: if applications are still writing, the drain is slower and the ETA longer.
- **Dirty RAM bar** — percentage of the kernel's dirty-data limit, computed from `vm.dirty_bytes`, or from `vm.dirty_ratio × MemAvailable`. This is an estimate of the point where the kernel starts stalling writers; throttling begins gradually before it.
- **Drive lines** — throughput, latency and busy % are **5-second time-weighted averages**, so bursty I/O does not flicker. Queue depth is the instantaneous value. The cache drive is the non-rotational disk in the volume group; the origin is the rotational one.
- **ext4 init** — shown only while the `ext4lazyinit` kernel thread is running (a one-time job after `mkfs.ext4` that zeroes inode tables). Needs root. Progress comes from counting block groups flagged `ITABLE_ZEROED` via `dumpe2fs`, checked in the background **at most once a minute**. Speed is `groups zeroed ÷ elapsed time` averaged over the whole session (up to an hour of samples, shown after 2 minutes); `ETA = remaining groups ÷ speed`.

### LVM Cache

| Line | Meaning |
|---|---|
| **Cache Mode** | `writethrough` (safe: the slow disk always has a full copy), `writeback` (fast: dirty blocks live only on the cache until flushed) or `passthrough` |
| **Cache Pool** | Total size of the cache |
| **Cache Usage** | Share of the cache currently holding data |
| **Copied in** | Blocks promoted from the slow disk into the cache (cumulative, with the current rate). Needs `dmsetup`; shown as `n/a` if cachetop had to fall back to `lvs` |
| **Evicted** | Blocks demoted (dropped) from the cache, with the current rate |
| **Dirty Blocks** | Cache data not yet written to the slow disk. Shown in writeback mode, or whenever dirty blocks exist (for example leftovers right after leaving writeback); hidden in writethrough, which never holds dirty data |
| **Flush** | Net rate dirty blocks are being written back (`flushing`), or `growing` if new dirty data arrives faster. Includes an ETA. Shown together with Dirty Blocks |
| **Hit Ratio / Read Hits / Write Hits** | Exact hit and miss counts since the cache was attached |

**Reading the hit ratios:** under a write-heavy workload (such as installing games) most writes miss the cache, so the overall hit ratio looks poor even when the cache is doing its job for reads. Look at **Read Hits** for how well the cache serves your reads. In writethrough mode every write still goes to the slow disk.

### Real-time Status Bars

Percentage bars for cache usage, dirty blocks, and the three hit ratios. Hit-ratio bars are green above 80%, yellow from 60%, and red below. The dirty-blocks bar is always blue and appears only when the Dirty Blocks line does (writeback mode, or dirty blocks present).

### Stalled flush

In writeback mode dm-cache writes dirty blocks back to the slow disk only when the volume has been quiet for a moment. If something keeps using the volume (a download, `ext4lazyinit`, the journal), the dirty count can sit still or grow while the disks look idle. cachetop's verdict then reads **"Stalled: writeback is holding N GB ... but nothing is flushing it"** (shown when writeback holds at least 1 GB, nothing is flushing it, and no device is busy). Stopping whatever uses the volume (closing programs, unmounting it) lets the backlog drain at disk speed.

### Interactive Volume Selection

- **Auto-Detection**: with no arguments cachetop tries `vg_games/games` first, then scans for cache volumes
- **Smart Selection**: a single volume is used automatically; several show a menu
- **Arrow Navigation**: ↑/↓ to move, Enter to select
- **Manual Override**: `--vg` and `--lv`; **Force Menu**: `--pick`

## Cache Policies and Their Impact

### Writethrough vs Writeback
- **Writethrough**: Writes go to both the cache and the slow storage
  - Lower write hit ratios
  - Better data safety: losing the cache drive loses no data
  - Writes run at slow-disk speed
- **Writeback**: Writes can land on the cache first and reach the slow storage later
  - Dirty blocks exist only on the cache until flushed — keep a UPS connected
  - Large sequential writes may still go straight to the slow disk: dm-cache does not treat a big sequential stream as hot data, so writeback is not a guaranteed install-speed boost
  - After an unclean shutdown dm-cache cannot trust which blocks are dirty, so it has to write cached blocks back

### Cache Modes
- **writeback**: Best performance, data temporarily in cache only
- **writethrough**: Safer, data written to both cache and origin
- **passthrough**: Cache disabled for writes, I/O goes to slow storage

## Troubleshooting Common Issues

### Low Hit Ratios (<50%)
- **Possible causes**: Cache too small, random I/O patterns, cache warming up, a write-heavy period (check **Read Hits** instead)
- **Solutions**: Increase cache size, check workload patterns, wait for warm-up

### High Dirty Blocks
- **Possible causes**: Write-heavy workload in writeback mode, slow backing disk, a disk busy with reads or housekeeping
- **Solutions**: Look at the pipeline's bottleneck line, check the slow disk's latency and busy %, consider writethrough

### Slow Disk Shows 100% Busy With Little Throughput
- **Possible causes**: A shingled (SMR) disk stalling under sustained writes, mixed read/write load, background work such as `ext4lazyinit` or cache migration (the "Copied in" rate)
- **Solutions**: Let one-time jobs finish, avoid mixing big installs with verification, consider a CMR disk or a separate fast install drive

### Cache Not Filling (Low usage)
- **Possible causes**: Light workload, cache larger than working set, recent setup
- **Solutions**: Normal for light workloads, monitor during peak usage

## Command Line Options

```bash
cachetop [OPTIONS]

Options:
  --vg VG_NAME           Volume group name (optional - auto-detected if not specified)
  --lv LV_NAME           Logical volume name (optional - auto-detected if not specified)
  --interval SECONDS     Refresh interval in seconds, decimals allowed (default: 1)
  --pick                 Force interactive selection menu even with a single cache volume
  --version              Show version
  -h, --help             Show help message
```

Keys while running: `+`/`=` faster (halves the interval, minimum 0.1 s), `-`/`_` slower (doubles it, maximum 10 s), `q` quit.

### Auto-Detection Behavior

1. **No arguments**: tries `vg_games/games` with one quick query, then scans for cache volumes
   - **Single volume**: Uses it automatically
   - **Multiple volumes**: Shows interactive selection menu
   - **No volumes**: Shows error and exits
2. **With --pick**: Always shows the interactive selection menu
3. **With --vg and --lv**: Uses the specified volume directly

## Examples

```bash
# Simple auto-detection
sudo python3 cachetop.py

# Faster refresh
sudo python3 cachetop.py --interval 0.5

# Force selection menu
sudo python3 cachetop.py --pick

# A specific volume
sudo python3 cachetop.py --vg vg_games --lv games

# Database server, slower refresh
sudo python3 cachetop.py --vg vg_db --lv database --interval 5
```

## Performance Tips

1. **Cache Sizing**: Start with 10-20% of your slow storage size
2. **SSD Selection**: Use high-quality SSDs with good random I/O performance
3. **Monitor Regularly**: Check during peak usage periods
4. **Tune Based on Workload**:
   - Read-heavy: Focus on cache size
   - Write-heavy: Consider writeback only with a UPS, and watch the flush ETA
   - Mixed: Balance based on hit ratio analysis
5. **Terminal**: Use a window at least 100 columns wide
6. **Color Interpretation**: Green is healthy, red needs attention

## Technical Notes

- **Cache counters** come from `dmsetup status <vg>-<lv>` (the dm-cache target status line): used/total blocks, dirty blocks, read/write hits and misses, promotions, demotions, block size and mode. If `dmsetup` is unusable, cachetop falls back to `lvs`, which does not report promotions or demotions.
- **Drives**: `pvs` finds the physical volumes of the volume group once; the rotational one is the slow disk, the non-rotational one is the cache drive. Rates come from `/proc/diskstats` snapshots compared over a 5 second window.
- **RAM**: dirty data and writeback come from `/proc/meminfo`; the dirty limit is derived from `vm.dirty_bytes` / `vm.dirty_ratio` and `MemAvailable` (an approximation of what the kernel calls dirtyable memory).
- **ETA smoothing**: RAM drain and LVM flush rates use about 10 seconds of samples; the ext4 init speed uses up to an hour.
- **ext4 init** runs `dumpe2fs` in a background thread so a busy disk never blocks the screen.
- **Rendering**: each frame is drawn with a single write on the terminal's alternate screen, at a steady rate.
- **Layout**: fixed 100 columns (`MAX_WIDTH` / `BAR_WIDTH` and the `PIPE_*` constants at the top of `cachetop.py`).
- **Sudo**: when not already root, cachetop prefixes its LVM queries with `sudo`; running the whole program under `sudo` avoids repeated prompts.

## Compatibility

- **LVM2**: Version 2.02.95+ (cache support required)
- **Kernel**: Linux 3.9+ (dm-cache support)
- **Python**: 3.7+
- **Terminal**: ANSI color and Unicode box-drawing characters, at least 100 columns

## Files in This Directory

- `cachetop.py` - Main monitoring script
- `README.md` - This documentation
- `RELEASE_NOTES.md` - Release history
- `BUILD.md` - Building and deployment guide
- `build.sh` - Binary build script
- `install.sh` - Installation script
- `Makefile` - Build automation
- `setup.py` - Python package setup
- `requirements.txt` - Runtime dependencies (none)
- `requirements-build.txt` - Build dependencies
- `.github/workflows/` - CI/CD automation

## Building from Source

See [BUILD.md](BUILD.md) for detailed instructions on:
- Creating binary executables
- Setting up GitHub Actions
- Distribution and packaging
- Troubleshooting build issues

Quick build:
```bash
./build.sh                    # Build binary
make install-binary          # Install system-wide
```

## License

This tool is provided as-is for educational and monitoring purposes. Use at your own discretion.
