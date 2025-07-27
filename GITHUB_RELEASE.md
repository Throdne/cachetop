# GitHub Release Notes for v2025.07

Copy this content when creating your GitHub release:

---

## cachetop v2025.07 - Initial Release 🎉

**Real-time LVM cache monitoring tool with htop-style interface**

### 🚀 Quick Install

**Binary (Recommended):**
```bash
# Download and install
wget https://github.com/Throdne/cachetop/releases/download/v2025.07/cachetop-linux-x64
chmod +x cachetop-linux-x64
sudo mv cachetop-linux-x64 /usr/local/bin/cachetop

# Or use install script
curl -sSL https://raw.githubusercontent.com/Throdne/cachetop/main/install.sh | bash
```

**From Source:**
```bash
git clone https://github.com/Throdne/cachetop.git
cd cachetop && make binary && make install-binary
```

### ✨ Key Features

- 📊 **Real-time LVM cache monitoring** with live statistics
- 🎨 **htop-style interface** with dynamic terminal sizing
- 🔍 **Auto-detection** of LVM cache volumes with interactive selection
- 📈 **Historical trends** with ASCII line graphs
- 🌈 **Color-coded performance** indicators (green/yellow/red)
- 🎯 **Dual-color cache bars** showing read vs write usage
- ⚙️ **Configurable** refresh intervals and history depth
- 🚀 **Single binary** - no Python installation required!

### 📊 What You Get

```
cachetop - vg_games/games
Cache Pool:   32.0GB total
Cache Usage:  45.2% (14.5GB used)
  ├─ Reads:   ~8.7GB (7048 blocks)  
  └─ Writes:  ~5.8GB (4681 blocks)
Hit Ratio:    89.5% (45231 operations)

Real-time Status:
Cache Usage   [████████████████████░░░░░░░░░] 45.2%
Hit Ratio     [████████████████████████████░] 89.5%
```

### 🎯 Usage Examples

```bash
cachetop                    # Auto-detect and monitor
cachetop --vg vg --lv lv   # Monitor specific volume  
cachetop --interval 1      # Fast refresh
cachetop --pick            # Force volume selection
cachetop --help            # Show all options
```

### 🛠 Requirements

- **OS**: Linux with LVM2 2.02.95+
- **Kernel**: dm-cache support (Linux 3.9+)
- **Permissions**: sudo access for LVM commands
- **Python**: 3.6+ (binary version: none! Built with 3.13.5)

### 📦 What's Included

- `cachetop-linux-x64` - Single-file binary executable (~7.3MB)
- `cachetop-source.tar.gz` - Source code package
- Complete documentation and build scripts

### 🔧 Technical Details

- **Zero dependencies** (uses only Python standard library)
- **Performance-based color coding** for instant status assessment
- **Dynamic width calculation** adapts to any terminal size
- **Estimated read/write distribution** from operation ratios
- **Graceful error handling** for missing LVM or permissions

Perfect for system administrators, database optimization, gaming setups, and storage performance tuning!

**Full documentation**: https://github.com/Throdne/cachetop#readme
