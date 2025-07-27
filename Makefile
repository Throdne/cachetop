.PHONY: help install build clean test binary package all

help:			## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:		## Install build dependencies
	pip install -r requirements-build.txt

build: binary		## Build binary (alias for binary target)

binary:			## Create binary executable with PyInstaller
	@echo "🔧 Building cachetop binary..."
	./build.sh

package:		## Build Python package
	@echo "📦 Building Python package..."
	python -m build

test:			## Test the script
	@echo "🧪 Testing cachetop..."
	python -m py_compile cachetop.py
	python cachetop.py --help

clean:			## Clean build artifacts
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/ dist/ *.spec *.egg-info/
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

install-binary:		## Install binary to /usr/local/bin (requires sudo)
	@if [ ! -f "dist/cachetop" ]; then echo "❌ Binary not found. Run 'make binary' first."; exit 1; fi
	@echo "📥 Installing cachetop to /usr/local/bin..."
	sudo cp dist/cachetop /usr/local/bin/
	@echo "✅ cachetop installed! You can now run 'cachetop' from anywhere."

uninstall:		## Remove installed binary
	@echo "🗑️  Removing cachetop from /usr/local/bin..."
	sudo rm -f /usr/local/bin/cachetop
	@echo "✅ cachetop uninstalled."

all: clean install binary package	## Clean, install deps, build binary and package

# Development targets
dev-install:		## Install in development mode
	pip install -e .

dev-test:		## Run development tests
	python cachetop.py --help
	@echo "✅ Development tests passed"
