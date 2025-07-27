#!/bin/bash
# Install script for cachetop

set -e

INSTALL_DIR="/usr/local/bin"
SCRIPT_NAME="cachetop"
GITHUB_REPO="yourusername/cachetop"  # Update with actual repo
VERSION="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 cachetop Installation Script${NC}"
echo "=================================="

# Check if running as root for binary installation
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}⚠️  This script needs sudo privileges to install to ${INSTALL_DIR}${NC}"
        echo "You will be prompted for your password."
    fi
}

# Install binary from GitHub releases
install_binary() {
    echo -e "${BLUE}📦 Installing binary from GitHub releases...${NC}"
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Download latest release
    echo "Downloading latest cachetop binary..."
    DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/releases/latest/download/cachetop-linux-x64"
    
    if command -v wget &> /dev/null; then
        wget -O cachetop "$DOWNLOAD_URL"
    elif command -v curl &> /dev/null; then
        curl -L -o cachetop "$DOWNLOAD_URL"
    else
        echo -e "${RED}❌ Neither wget nor curl found. Please install one of them.${NC}"
        exit 1
    fi
    
    # Make executable and install
    chmod +x cachetop
    sudo cp cachetop "$INSTALL_DIR/"
    
    # Cleanup
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
    
    echo -e "${GREEN}✅ Binary installed to ${INSTALL_DIR}/cachetop${NC}"
}

# Install from source
install_from_source() {
    echo -e "${BLUE}🔧 Installing from source...${NC}"
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 is required but not installed.${NC}"
        exit 1
    fi
    
    # Clone or download source
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    echo "Downloading source code..."
    if command -v git &> /dev/null; then
        git clone "https://github.com/${GITHUB_REPO}.git" .
    else
        # Download zip
        SOURCE_URL="https://github.com/${GITHUB_REPO}/archive/refs/heads/main.zip"
        if command -v wget &> /dev/null; then
            wget -O source.zip "$SOURCE_URL"
        elif command -v curl &> /dev/null; then
            curl -L -o source.zip "$SOURCE_URL"
        fi
        unzip source.zip
        cd */
    fi
    
    # Install PyInstaller and build
    echo "Installing build dependencies..."
    pip3 install pyinstaller
    
    echo "Building binary..."
    pyinstaller --onefile --name cachetop cachetop.py
    
    # Install binary
    sudo cp dist/cachetop "$INSTALL_DIR/"
    
    # Cleanup
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
    
    echo -e "${GREEN}✅ Built and installed to ${INSTALL_DIR}/cachetop${NC}"
}

# Install using pip (if available on PyPI)
install_pip() {
    echo -e "${BLUE}🐍 Installing via pip...${NC}"
    pip3 install cachetop
    echo -e "${GREEN}✅ Installed via pip${NC}"
}

# Main installation logic
main() {
    echo "Choose installation method:"
    echo "1) Binary from GitHub releases (recommended)"
    echo "2) Build from source"
    echo "3) Install via pip (if available)"
    echo
    read -p "Enter choice (1-3): " choice
    
    case $choice in
        1)
            check_sudo
            install_binary
            ;;
        2)
            check_sudo
            install_from_source
            ;;
        3)
            install_pip
            ;;
        *)
            echo -e "${RED}❌ Invalid choice${NC}"
            exit 1
            ;;
    esac
    
    echo
    echo -e "${GREEN}🎉 Installation complete!${NC}"
    echo
    echo "Usage:"
    echo "  cachetop                    # Auto-detect LVM cache volumes"
    echo "  cachetop --help             # Show all options"
    echo "  cachetop --vg vg --lv lv    # Monitor specific volume"
    echo
    echo "To uninstall:"
    echo "  sudo rm ${INSTALL_DIR}/cachetop"
}

# Run main function
main "$@"
