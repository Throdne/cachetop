# Screenshots Directory

This directory contains screenshots for the cachetop README.md

## Required Screenshots:

1. **cachetop-main.png** - Main interface showing:
   - Real-time cache statistics
   - Dual-color progress bars (read/write)
   - Hit ratio displays
   - Historical trend graphs
   - Terminal-responsive layout

2. **cachetop-selection.png** - Volume selection menu showing:
   - Auto-detection message
   - Interactive menu with arrow key navigation
   - Multiple cache volumes listed
   - Selection highlighting

## How to Create Screenshots:

### 1. Main Interface Screenshot
```bash
# Start cachetop (ensure you have LVM cache configured)
cachetop

# Let it run for a few minutes to build history
# Take screenshot of the full terminal window
```

### 2. Selection Menu Screenshot
```bash
# If you have multiple cache volumes configured:
cachetop --pick

# Or simulate with multiple volumes if available
# Take screenshot of the selection menu
```

## Screenshot Guidelines:

- **Terminal size**: Recommended 120x30 or larger for best display
- **File format**: PNG with transparent background preferred
- **Quality**: High resolution for clarity in documentation
- **Content**: Show realistic data, not just test values
- **Colors**: Ensure all color coding is visible (green/yellow/red/blue)

## Alternative if No LVM Cache Available:

If you don't have LVM cache configured, you can:
1. Use the sample output shown in the README (text format)
2. Create mockup screenshots using terminal recording tools
3. Document the interface with detailed text descriptions

The sample output in the README shows exactly what the interface looks like.
