# cachetop

A real-time monitoring tool for LVM cache performance with htop-style visual displays. This Python script provides comprehensive insights into your LVM cache usage, hit ratios, and performance trends over time.

## Features

- 🔄 Real-time cache statistics monitoring
- 📊 Visual progress bars with color-coded status indicators
- 📈 Historical trend graphs for performance analysis
- 🎨 Dual-color cache usage visualization (read vs write)
- 🖥️ Terminal-based interface similar to htop
- ⚙️ Configurable refresh intervals and history depth
- 📏 Dynamic terminal sizing - bars and graphs automatically adjust to window width
- 🌈 Performance-based color coding for instant status assessment
- 🔍 Automatic LVM cache volume detection
- 📋 Interactive volume selection menu with arrow key navigation
- ⚡ Smart defaults with manual override options

## Installation

### Binary Installation (Recommended)

**Quick install:**
```bash
# Download and run install script
curl -sSL https://raw.githubusercontent.com/yourusername/cachetop/main/install.sh | bash
```

**Manual binary install:**
```bash
# Download latest binary
wget https://github.com/yourusername/cachetop/releases/latest/download/cachetop-linux-x64
chmod +x cachetop-linux-x64
sudo mv cachetop-linux-x64 /usr/local/bin/cachetop
```

### From Source

```bash
# Clone repository
git clone https://github.com/yourusername/cachetop.git
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

**Binary:**
```bash
# Auto-detect and monitor LVM cache
cachetop

# Show help
cachetop --help

# Monitor specific volume
cachetop --vg my_vg --lv my_lv
```

**From source:**
```bash
```bash
# Basic usage with auto-detection
python3 cachetop.py

# Fast monitoring with longer history
python3 cachetop.py --interval 1 --history 120

# Force interactive selection menu
python3 cachetop.py --pick

# Monitor specific volume (skip auto-detection)
# Gaming setup with fast refresh
python3 cachetop.py --vg vg_games --lv games --interval 1

# Database monitoring with extended history
python3 cachetop.py --vg vg_db --lv database --interval 5 --history 120

# System cache monitoring
python3 cachetop.py --vg vg_system --lv root
```
```

## Requirements

- Python 3.6+
- LVM2 with cache support
- sudo privileges (for accessing LVM statistics)
- A configured LVM cache setup

## Understanding the Data Points

### Current Statistics Section

#### Cache Pool
```
Cache Pool: 32.0GB total
```
- **What it is**: The total size of your cache pool (SSD/fast storage)
- **What it means**: The maximum amount of data that can be cached
- **Good values**: Depends on your workload, typically 10-20% of your slow storage

#### Cache Usage
```
Cache Usage: 45.2% (14.5GB used)
  ├─ Reads:   ~9.1GB (2234 blocks)
  └─ Writes:  ~5.4GB (1322 blocks)
```
- **What it is**: How much of your cache is currently occupied
- **Estimation**: Read/write breakdown is estimated based on operation ratios
- **What it means**: 
  - Higher usage = more data is cached (good for performance)
  - 100% usage = cache is full, may need tuning
- **Good values**: 70-95% for active workloads

#### Dirty Blocks
```
Dirty Blocks: 12.3% (3.9GB dirty)
```
- **What it is**: Cached data that has been modified but not yet written to slow storage
- **What it means**: 
  - High dirty ratio = more pending writes to slow storage
  - Very high values may indicate write bottlenecks
- **Good values**: <20% (depends on write policy)
- **Red flags**: >30% may indicate performance issues
- **Display**: Always shown in blue for easy identification

#### Hit Ratios
```
Hit Ratio:    89.5% (45231 total operations)
Read Hits:    92.1% (28934 read operations)
Write Hits:   85.2% (16297 write operations)
```
- **What it is**: Percentage of requests served from cache vs slow storage
- **What it means**:
  - **Total Hit Ratio**: Overall cache effectiveness
  - **Read Hits**: How often reads are served from cache
  - **Write Hits**: How often writes go to cache (vs slow storage)
- **Good values**: 
  - Total: >80% excellent, >60% good, <50% may need tuning
  - Reads: Usually higher than writes
  - Writes: Depends on write policy (writethrough vs writeback)

### Real-time Status Bars

#### Cache Usage Bar (Dual-Color)
```
Cache Usage   [████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 45.2%
              █ Read cache  █ Write cache  ░ Free
```
- **Green (█)**: Estimated cache blocks used for read data
- **Red (█)**: Estimated cache blocks used for write data  
- **Gray (░)**: Free cache space
- **What it tells you**: Whether your cache is read-heavy or write-heavy

#### Individual Performance Bars
Performance bars use dynamic color coding based on effectiveness:
- **🟢 Green**: Excellent performance (>80% hit ratio)
- **🟡 Yellow**: Good performance (60-80% hit ratio)
- **🔴 Red**: Needs attention (<60% hit ratio)
- **🔵 Blue**: Dirty blocks (always blue for easy identification)

#### Dynamic Terminal Sizing
- **Responsive Design**: Bars and graphs automatically adjust to your terminal width
- **Real-time Adaptation**: Resize your terminal window and see immediate changes on next refresh
- **Optimal Usage**: Makes full use of available screen space for better data visualization
- **Smart Minimums**: Maintains readability even in narrow terminal windows

#### Interactive Volume Selection
- **Auto-Detection**: Automatically finds and uses LVM cache volumes
- **Smart Selection**: Single volume auto-selected, multiple volumes show menu
- **Arrow Navigation**: Use ↑/↓ keys to navigate, Enter to select
- **Manual Override**: Use `--vg` and `--lv` for direct specification
- **Force Menu**: Use `--pick` to always show selection interface

### Historical Trends

#### Cache Usage Over Time
Shows how cache utilization changes over time:
- **Rising trend**: Cache warming up or increasing workload
- **Stable high**: Well-utilized cache
- **Fluctuating**: Variable workload patterns
- **Graph width**: Automatically adjusts to terminal size for maximum data points

#### Hit Ratio Trends
- **Stable high ratios**: Well-tuned cache
- **Declining ratios**: May need cache size increase or policy adjustment
- **Low read hits**: Consider larger cache or different algorithms
- **Low write hits**: May indicate writethrough policy or write-heavy workload
- **Color coding**: Headers use different colors to distinguish read/write trends

## Cache Policies and Their Impact

### Writethrough vs Writeback
- **Writethrough**: Writes go to both cache and slow storage immediately
  - Lower write hit ratios
  - Better data safety
  - Higher write latency
- **Writeback**: Writes go to cache first, written to slow storage later
  - Higher write hit ratios
  - Higher dirty block ratios
  - Better write performance

### Cache Modes
- **writeback**: Best performance, data temporarily in cache only
- **writethrough**: Safer, data written to both cache and origin
- **passthrough**: Cache disabled, all I/O goes to slow storage

## Troubleshooting Common Issues

### Low Hit Ratios (<50%)
- **Possible causes**: Cache too small, random I/O patterns, cache warming up
- **Solutions**: Increase cache size, check workload patterns, wait for warm-up

### High Dirty Blocks (>30%)
- **Possible causes**: Write-heavy workload, slow backend storage, large sequential writes
- **Solutions**: Check backend disk performance, consider cache policy adjustment

### Cache Not Filling (Low usage)
- **Possible causes**: Light workload, cache larger than working set, recent setup
- **Solutions**: Normal for light workloads, monitor during peak usage

### Fluctuating Performance
- **Possible causes**: Variable workload, background processes, cache thrashing
- **Solutions**: Analyze workload patterns, consider cache size adjustment

## Command Line Options

```bash
python3 cachetop.py [OPTIONS]

Options:
  --vg VG_NAME           Volume group name (optional - auto-detected if not specified)
  --lv LV_NAME           Logical volume name (optional - auto-detected if not specified)
  --interval SECONDS     Refresh interval in seconds (default: 2)
  --history SAMPLES      Number of historical samples to keep (default: 60)
  --pick                 Force interactive selection menu even with single cache volume
  -h, --help            Show help message
```

### Auto-Detection Behavior

1. **No arguments**: Automatically detects cache volumes
   - **Single volume**: Uses it automatically
   - **Multiple volumes**: Shows interactive selection menu
   - **No volumes**: Shows error and exits

2. **With --pick**: Always shows interactive selection menu

3. **With --vg and --lv**: Uses specified volumes directly

## Examples

### Auto-Detection (Recommended)
```bash
# Simple auto-detection
python3 lvm_cache_status.py

# Auto-detection with custom settings
python3 lvm_cache_status.py --interval 1 --history 120

# Force selection menu
python3 lvm_cache_status.py --pick
```

### Manual Specification
```bash
# Gaming setup with manual volume specification
python3 lvm_cache_status.py --vg vg_games --lv games --interval 1

# Database server monitoring
python3 lvm_cache_status.py --vg vg_db --lv database --interval 5 --history 120

# System cache monitoring
python3 lvm_cache_status.py --vg vg_system --lv root
```

## Performance Tips

1. **Cache Sizing**: Start with 10-20% of your slow storage size
2. **SSD Selection**: Use high-quality SSDs with good random I/O performance
3. **Monitor Regularly**: Check during peak usage periods
4. **Tune Based on Workload**: 
   - Read-heavy: Focus on cache size
   - Write-heavy: Consider writeback policy
   - Mixed: Balance based on hit ratio analysis
5. **Terminal Optimization**: Use a wider terminal for more detailed historical graphs
6. **Color Interpretation**: Green bars indicate good performance, red bars need attention

## Technical Notes

- **Block Size**: Automatically detected from LVM configuration
- **Estimation Method**: Read/write cache distribution estimated from operation ratios
- **Refresh Rate**: Configurable, but too frequent updates may impact performance
- **Sudo Requirements**: Needed for `lvs` command access to cache statistics
- **Terminal Sizing**: Uses `shutil.get_terminal_size()` with fallbacks for compatibility
- **Dynamic Adaptation**: Bar and graph widths recalculated on every refresh cycle
- **Performance**: Efficient terminal size detection with minimal overhead

## Compatibility

- **LVM2**: Version 2.02.95+ (cache support required)
- **Kernel**: Linux 3.9+ (dm-cache support)
- **Python**: 3.6+ (f-string support)
- **Terminal**: Any terminal with ANSI color support

## Files in This Directory

- `cachetop.py` - Main monitoring script
- `README.md` - This documentation
- `BUILD.md` - Building and deployment guide
- `build.sh` - Binary build script
- `install.sh` - Installation script
- `Makefile` - Build automation
- `setup.py` - Python package setup
- `requirements.txt` - Runtime dependencies (none)
- `requirements-build.txt` - Build dependencies
- `.github/workflows/` - CI/CD automation
- `create_storage.sh` - Helper script for LVM cache setup (if present)
- `verify_lvm_cache.sh` - Cache verification script (if present)

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
