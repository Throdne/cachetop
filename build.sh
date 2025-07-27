#!/bin/bash
# Build script for creating cachetop binary executable

set -e

echo "🔧 Building cachetop binary executable..."

# Create virtual environment if it doesn't exist
if [ ! -d "build-env" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv build-env
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source build-env/bin/activate

# Check if PyInstaller is installed in venv
if ! command -v pyinstaller &> /dev/null; then
    echo "📦 Installing PyInstaller in virtual environment..."
    pip install pyinstaller
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.spec

# Create binary with PyInstaller
echo "⚙️  Creating binary executable..."
pyinstaller \
    --onefile \
    --name cachetop \
    --console \
    --add-data "README.md:." \
    --hidden-import termios \
    --hidden-import tty \
    cachetop.py

# Deactivate virtual environment
deactivate

# Verify the build
if [ -f "dist/cachetop" ]; then
    echo "✅ Binary created successfully: dist/cachetop"
    echo "📏 File size: $(du -h dist/cachetop | cut -f1)"
    echo ""
    echo "🚀 To install system-wide:"
    echo "   sudo cp dist/cachetop /usr/local/bin/"
    echo ""
    echo "🧪 To test locally:"
    echo "   ./dist/cachetop --help"
else
    echo "❌ Build failed!"
    exit 1
fi
