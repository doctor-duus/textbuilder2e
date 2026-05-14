# Textbuilder2e

Convert [Pathbuilder 2e](https://pathbuilder2e.com/) JSON exports to human-readable text formats.

## Features

- **Multiple templates**: Build progression, static sheet, or condensed format
- **Clipboard support**: Read JSON directly from clipboard (macOS)
- **Remaster compatible**: Uses ability modifiers (not scores), no alignment

## Templates

| Template | Description |
|----------|-------------|
| `build` (default) | Level-by-level progression showing choices at each level |
| `static` | Complete character sheet with all stats and features |
| `condensed` | Compact format: feats grouped by type, no levels shown |

## Installation

Download `textbuilder2e.py` and run with Python 3.10+.

```bash
# Make it executable (optional)
chmod +x textbuilder2e.py

# Or add to your PATH
ln -s /path/to/textbuilder2e.py ~/bin/textbuilder
```

## Usage

First, export your character from Pathbuilder 2e:
1. Open your character in Pathbuilder 2e
2. Menu → Export Character → Export to Foundry VTT (JSON)
3. Save the JSON file

Then convert to text:

```bash
# Build progression (default)
textbuilder2e.py character.json

# Static character sheet
textbuilder2e.py character.json -t static

# Condensed format
textbuilder2e.py character.json -t condensed

# Read from clipboard, print to stdout
textbuilder2e.py -c --stdout

# Specify output file
textbuilder2e.py character.json -t static -o mycharacter.txt
```

## Output Examples

See the [examples/](examples/) folder for sample output:
- `glimpse.json` - Pathbuilder 2e JSON export
- `glimpse-static.txt` - Static character sheet
- `glimpse-build.txt` - Build progression
- `glimpse-condensed.txt` - Condensed format

### Header (all templates)
```
============================================================
  Glimpse, goblin xbowslinger (rogue) 12th
  STR +0  DEX +5  CON +4  INT +2  WIS +0  CHA +5
============================================================
```

### Static Template
Shows complete character sheet: basic info, defenses, saves, skills, class features, feats with levels, equipment.

### Build Template
Shows level-by-level progression: ancestry/background choices, class features, feat selections at each level, ability boosts.

### Condensed Template
Compact format for sharing: just the key choices with feats grouped by type (Ancestry, Class, Skill, General).

## Options

| Flag | Description |
|------|-------------|
| `-t`, `--template` | Output template: `build`, `static`, or `condensed` |
| `-w`, `--width` | Line width for word wrap (default: 71, 0 to disable) |
| `-o`, `--output` | Output file (default: `<input>.txt`) |
| `-c`, `--clipboard` | Read JSON from clipboard (macOS) |
| `--stdout` | Print to stdout instead of file |
| `--no-prompt` | Skip interactive skill increase prompts (build only) |

## Known Issues

### 1. ~~INT-based skill training not tracked~~ (Fixed)

When a character's INT modifier increases, they gain a new trained skill. The build template now detects this and prompts for the skill selection.

### 2. Some class features may be missing

For certain classes (e.g., Commander), higher-level class feature choices (like Expert Tactician at level 7) may not be recorded, while level 1 choices (like Tactics) are shown.

**To fix:**
- Investigate how Pathbuilder stores class feature choices in the JSON
- Check if choices are in `specials`, `feats`, or another field
- Ensure all selectable class features are extracted and displayed

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)

## License

MIT License - feel free to use, modify, and share.

## Contributing

Issues and pull requests welcome!
