#!/bin/bash
# Release helper script for cachetop

VERSION="2025.07"
TAG="v${VERSION}"

echo "🚀 cachetop Release Helper - Version ${VERSION}"
echo "=================================================="

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not in a git repository. Please run from the project root."
    exit 1
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  You have uncommitted changes:"
    git status --short
    echo
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Release cancelled."
        exit 1
    fi
fi

echo "📋 Pre-release checklist:"
echo "========================"

# Build and test
echo "🔧 Building binary..."
if ./build.sh; then
    echo "✅ Binary build successful"
else
    echo "❌ Binary build failed"
    exit 1
fi

# Test binary
echo "🧪 Testing binary..."
if ./dist/cachetop --version; then
    echo "✅ Binary test successful"
else
    echo "❌ Binary test failed"
    exit 1
fi

echo
echo "📝 Release Information:"
echo "======================"
echo "Version: ${VERSION}"
echo "Tag: ${TAG}"
echo "Binary: dist/cachetop ($(du -h dist/cachetop | cut -f1))"
echo

# Show what will be tagged
echo "📦 Files to be released:"
echo "========================"
echo "✅ cachetop.py - Main script"
echo "✅ README.md - Documentation"
echo "✅ BUILD.md - Build instructions"
echo "✅ RELEASE_NOTES.md - Full release notes"
echo "✅ GITHUB_RELEASE.md - GitHub release template"
echo "✅ build.sh - Build script"
echo "✅ install.sh - Installation script"
echo "✅ Makefile - Build automation"
echo "✅ setup.py - Python packaging"
echo "✅ .github/workflows/ - CI/CD"

echo
echo "🏷️  Ready to create release tag?"
echo "This will:"
echo "1. Create git tag: ${TAG}"
echo "2. Push tag to origin"
echo "3. Trigger GitHub Actions build"
echo "4. Create automated GitHub release"
echo

read -p "Create release tag ${TAG}? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🏷️  Creating tag..."
    git tag -a "${TAG}" -m "Release ${VERSION}"
    
    echo "📤 Pushing tag to origin..."
    git push origin "${TAG}"
    
    echo
    echo "🎉 Release tag created successfully!"
    echo
    echo "📋 Next steps:"
    echo "1. GitHub Actions will automatically build the binary"
    echo "2. Go to: https://github.com/Throdne/cachetop/releases"
    echo "3. Edit the auto-created release"
    echo "4. Copy content from GITHUB_RELEASE.md"
    echo "5. Upload any additional assets if needed"
    echo
    echo "🔗 Direct link: https://github.com/Throdne/cachetop/releases/tag/${TAG}"
    
else
    echo "Release cancelled."
    echo
    echo "💡 To create the release later:"
    echo "   git tag -a ${TAG} -m 'Release ${VERSION}'"
    echo "   git push origin ${TAG}"
fi

echo
echo "📖 Release notes template available in:"
echo "   - RELEASE_NOTES.md (full documentation)"
echo "   - GITHUB_RELEASE.md (GitHub release description)"
