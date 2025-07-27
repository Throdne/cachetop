# Release Notes

## Version 2025.07 - Initial Release (July 27, 2025)

🎉 **First stable release of cachetop** - A real-time LVM cache monitoring tool inspired by htop!

### ✨ Key Features

#### 📊 **Real-time Monitoring**
- Live cache usage statistics with color-coded performance indicators
- Read vs write cache visualization with dual-color progress bars
- Hit ratio tracking for both read and write operations
- Dirty block monitoring with dedicated blue visualization
- Historical trend graphs showing performance over time

#### 🎨 **Visual Interface**
- **htop-style interface** with ANSI color support
- **Dynamic terminal sizing** - bars and graphs automatically adjust to window width
- **Performance-based color coding**: Green (good) → Yellow (moderate) → Red (poor)
- **Dual-color cache bars**: Green for read cache, red for write cache
- **Interactive selection menu** with arrow key navigation

#### 🔍 **Smart Auto-Detection**
- Automatic LVM cache volume detection
- Interactive volume selection when multiple cache volumes exist
- Manual volume specification for specific use cases
- Graceful fallback handling for missing or inaccessible volumes

#### ⚙️ **Flexible Configuration**
- Configurable refresh intervals (default: 2 seconds)
- Adjustable history depth (default: 60 samples)
- Force interactive selection mode (`--pick` flag)
- Command-line argument support for automation

### 🚀 **Installation Options**

#### Binary Executable (Recommended)
```bash
# Quick install via script
curl -sSL https://raw.githubusercontent.com/Throdne/cachetop/main/install.sh | bash

# Manual binary install
wget https://github.com/Throdne/cachetop/releases/latest/download/cachetop-linux-x64
chmod +x cachetop-linux-x64
sudo mv cachetop-linux-x64 /usr/local/bin/cachetop
```

#### From Source
```bash
git clone https://github.com/Throdne/cachetop.git
cd cachetop
make binary && make install-binary
```

### 📈 **What cachetop Shows You**

- **Cache Pool Size**: Total allocated cache space
- **Cache Usage**: Percentage and size of used cache (split by read/write)
- **Dirty Blocks**: Modified data awaiting write to slow storage
- **Hit Ratios**: Cache effectiveness for total, read, and write operations
- **Historical Trends**: Performance graphs over time
- **Terminal-Responsive**: All visualizations adapt to your terminal size

### 🛠 **Technical Specifications**

- **Dependencies**: None! (Uses only Python standard library)
- **Python Support**: 3.6+ (f-string compatible)
- **LVM Requirements**: LVM2 2.02.95+ with cache support
- **Operating System**: Linux (dm-cache kernel support required)
- **Binary Size**: ~7.3MB (single-file executable)
- **Memory Usage**: ~15MB runtime
- **Startup Time**: ~100ms cold start

### 🎯 **Use Cases**

- **System Administrators**: Monitor LVM cache performance in real-time
- **Database Optimization**: Track cache effectiveness for database workloads
- **Gaming Setups**: Monitor game library cache performance
- **Storage Tuning**: Analyze cache hit ratios for optimization
- **Performance Debugging**: Identify storage bottlenecks

### 📋 **Example Usage**

```bash
# Auto-detect and monitor (most common)
cachetop

# Monitor specific volume
cachetop --vg vg_games --lv games

# Fast refresh with extended history
cachetop --interval 1 --history 120

# Force interactive selection
cachetop --pick

# Show help
cachetop --help
```

### 🔧 **Build and CI/CD Features**

- **Automated binary builds** with PyInstaller
- **GitHub Actions CI/CD** pipeline
- **Multi-Python version testing** (3.6 through 3.11)
- **Automated releases** on git tags
- **Professional packaging** with setup.py
- **Virtual environment isolation** for reproducible builds

### 📖 **Documentation**

- Comprehensive README with usage examples
- BUILD.md with detailed build instructions
- Inline help system (`--help` flag)
- Error handling with helpful messages
- Troubleshooting guides

### 🔐 **Security & Quality**

- **No external dependencies** - reduced attack surface
- **Transparent builds** via GitHub Actions
- **Auditable source code** - single Python file
- **Graceful error handling** for missing permissions
- **Input validation** for all parameters

### 🚦 **Performance Indicators**

The tool uses intuitive color coding:
- 🟢 **Green**: Good performance (>80% hit ratio)
- 🟡 **Yellow**: Moderate performance (60-80% hit ratio)
- 🔴 **Red**: Poor performance (<60% hit ratio)
- 🔵 **Blue**: Dirty blocks (always blue for easy identification)

### 📊 **Sample Output**

```
cachetop - vg_games/games
================================

Current Statistics:
Cache Pool:   32.0GB total
Cache Usage:  45.2% (14.5GB used)
  ├─ Reads:   ~8.7GB (7048 blocks)
  └─ Writes:  ~5.8GB (4681 blocks)
Dirty Blocks: 12.3% (3.9GB dirty)
Hit Ratio:    89.5% (45231 total operations)
Read Hits:    92.1% (28934 read operations)
Write Hits:   85.2% (16297 write operations)

Real-time Status:
Cache Usage   [████████████████████░░░░░░░░░] 45.2%
              █ Read cache  █ Write cache  ░ Free
Dirty Blocks  [████░░░░░░░░░░░░░░░░░░░░░░░░░░] 12.3%
Hit Ratio     [████████████████████████████░] 89.5%
```

### 🐛 **Known Limitations**

- Linux-only (requires dm-cache kernel module)
- Requires sudo privileges for LVM access
- Read/write cache distribution is estimated (not directly provided by LVM)
- Terminal width must be ≥40 characters for proper display

### 🔄 **Future Roadmap**

- Multi-platform support (BSD, macOS with potential LVM alternatives)
- JSON output mode for scripting
- Prometheus metrics export
- Configuration file support
- Plugin system for custom metrics

### 🙏 **Credits**

Inspired by the excellent monitoring tools:
- `htop` - Process monitoring
- `iotop` - I/O monitoring  
- `iftop` - Network monitoring

### 📝 **Installation Verification**

After installation, verify with:
```bash
cachetop --help
# Should display usage information

# If you have LVM cache configured:
cachetop
# Should auto-detect and start monitoring
```

---

**Full Changelog**: https://github.com/Throdne/cachetop/commits/v2025.07
