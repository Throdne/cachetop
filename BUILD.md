# Building and Deployment Guide

This document explains how to build cachetop as a binary executable and set up CI/CD with GitHub Actions.

## Building Binary Executable

### Quick Build

```bash
# Build binary using the provided script
./build.sh
```

The script will:
1. Create a virtual environment if needed
2. Install PyInstaller
3. Build a single-file executable
4. Output the binary to `dist/cachetop`

### Manual Build

```bash
# Create virtual environment
python3 -m venv build-env
source build-env/bin/activate

# Install PyInstaller
pip install pyinstaller

# Build binary
pyinstaller --onefile --name cachetop --console cachetop.py

# The binary will be in dist/cachetop
```

### Using Make

```bash
# Install dependencies and build everything
make all

# Just build binary
make binary

# Install binary system-wide
make install-binary

# Clean build artifacts
make clean
```

## Installation Options

### 1. Binary Installation (Recommended)

**Automated installation:**
```bash
curl -sSL https://raw.githubusercontent.com/yourusername/cachetop/main/install.sh | bash
```

**Manual installation:**
```bash
# Download from releases
wget https://github.com/yourusername/cachetop/releases/latest/download/cachetop-linux-x64
chmod +x cachetop-linux-x64
sudo mv cachetop-linux-x64 /usr/local/bin/cachetop
```

### 2. From Source

```bash
git clone https://github.com/yourusername/cachetop.git
cd cachetop
make binary
make install-binary
```

### 3. Python Package (if published to PyPI)

```bash
pip install cachetop
```

## GitHub Actions CI/CD

The project includes two GitHub Actions workflows:

### 1. Test Workflow (`.github/workflows/test.yml`)

Runs on every push and pull request:
- Tests Python syntax
- Validates help command
- Runs basic functionality tests

### 2. Build and Release Workflow (`.github/workflows/build.yml`)

Runs on tags and releases:
- Tests across multiple Python versions
- Builds binary executable
- Creates GitHub releases
- Uploads binary artifacts

### Setting Up Releases

1. **Tag a release:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **GitHub Actions will automatically:**
   - Run tests
   - Build binary
   - Create a GitHub release
   - Upload the binary as a release asset

### Customizing Workflows

Edit the workflow files to:
- Add more test environments
- Change build targets
- Modify release notes
- Add deployment steps

## Build Configuration

### PyInstaller Options

The build uses these PyInstaller options:
- `--onefile`: Create a single executable file
- `--name cachetop`: Set the executable name
- `--console`: Console application (not windowed)
- `--add-data "README.md:."`: Include README in binary
- `--hidden-import termios`: Ensure terminal modules are included
- `--hidden-import tty`: Ensure TTY modules are included

### Virtual Environment

The build process uses a virtual environment to:
- Isolate build dependencies
- Avoid conflicts with system packages
- Ensure reproducible builds

## Troubleshooting

### Build Issues

**Python externally managed environment:**
```bash
# Use virtual environment (handled automatically by build.sh)
python3 -m venv build-env
source build-env/bin/activate
pip install pyinstaller
```

**Missing dependencies:**
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt install python3-dev

# Install system dependencies (Arch Linux)
sudo pacman -S python python-pip
```

**Large binary size:**
The binary (~7MB) includes the Python interpreter and all dependencies. This is normal for PyInstaller builds.

### Runtime Issues

**Permission denied:**
```bash
chmod +x dist/cachetop
```

**Missing sudo privileges:**
The tool requires sudo to access LVM commands. Make sure the user is in the sudo group.

**LVM not found:**
Ensure LVM2 is installed and cache volumes are configured.

## Distribution

### GitHub Releases

1. Tag a version: `git tag v1.0.0`
2. Push tag: `git push origin v1.0.0`
3. GitHub Actions builds and releases automatically

### Package Managers

To submit to package managers:

**AUR (Arch Linux):**
- Create PKGBUILD file
- Submit to AUR

**Homebrew (macOS):**
- Create formula
- Submit PR to homebrew-core

**Snap:**
- Create snapcraft.yaml
- Publish to Snap Store

**AppImage:**
- Use PyInstaller output with AppImage tools

## Security Considerations

- Binary is built in GitHub Actions (transparent)
- No external dependencies reduce attack surface
- Source code is auditable
- Use GPG signing for releases (optional)

## Performance Notes

- Binary startup: ~100ms (cold start)
- Memory usage: ~15MB
- Single-file deployment simplifies distribution
- No Python installation required on target systems
