# Textbuilder2e

Convert [Pathbuilder 2e](https://pathbuilder2e.com/) or [Foundry VTT](https://foundryvtt.com/) PF2e JSON exports to human-readable text formats.

## Features

- **Multiple input sources**: Pathbuilder 2e and Foundry VTT PF2e (auto-detected)
- **Multiple templates**: Build progression, static sheet, or condensed format
- **Social media formats**: Reddit (markdown), Paizo forums (BBCode), and Bluesky (compact)
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

### From Pathbuilder 2e
1. Open your character in Pathbuilder 2e
2. Menu → Export Character → Export to Foundry VTT (JSON)
3. Save the JSON file

### From Foundry VTT
1. Right-click your character in the Actors sidebar
2. Export Data
3. Save the JSON file

Then convert to text:

```bash
# Build progression (default) -> character-build.txt
textbuilder2e.py character.json

# Static character sheet -> character-static.txt
textbuilder2e.py character.json -t static

# Condensed format -> character-condensed.txt
textbuilder2e.py character.json -t condensed

# Read from clipboard, print to stdout
textbuilder2e.py -c --stdout

# Specify output file
textbuilder2e.py character.json -t static -o mycharacter.txt

# Format for Reddit post -> character-reddit.txt
textbuilder2e.py character.json -p reddit

# Format for Paizo forums (BBCode) -> character-paizo.txt
textbuilder2e.py character.json -p paizo

# Format for Bluesky post (print to stdout)
textbuilder2e.py character.json -p bluesky --stdout
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

### Post Formats
For sharing builds on social media and forums:
- **reddit**: Markdown format with bold headings, feats grouped by type
- **reddit-build**: Full build progression in Reddit markdown
- **reddit-static**: Character sheet in Reddit markdown
- **paizo**: Compact Paizo BBCode (just feats + basic info)
- **paizo-build**: Full build progression in Paizo BBCode
- **paizo-static**: Character sheet in Paizo BBCode
- **bluesky**: Ultra-compact format (~300 chars) with just key class feats

## Options

| Flag | Description |
|------|-------------|
| `-t`, `--template` | Output template: `build`, `static`, or `condensed` |
| `-p`, `--post` | Post format: `reddit`, `reddit-build`, `reddit-static`, `paizo`, `paizo-build`, `paizo-static`, or `bluesky` |
| `--json-source` | Input format: `auto` (default), `pathbuilder`, or `foundry` |
| `-w`, `--width` | Line width for word wrap (default: 71, 0 to disable) |
| `-o`, `--output` | Output file (default: `<input>-<template>.txt`) |
| `-c`, `--clipboard` | Read JSON from clipboard (macOS) |
| `--stdout` | Print to stdout instead of file |
| `--no-prompt` | Skip interactive skill increase prompts (build only) |

## Known Issues

### 1. ~~INT-based skill training not tracked~~ (Fixed)

When a character's INT modifier increases, they gain a new trained skill. The build template now detects this and prompts for the skill selection.

### 2. ~~Class features all shown at level 1~~ (Partially Fixed)

Class features now display at their correct levels for Commander and common features (Weapon Specialization, Drilled Reactions, etc.). The `CLASS_FEATURE_LEVELS` mapping in the code can be extended for other classes.

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)

## License

MIT License - feel free to use, modify, and share.

## Contributing

Issues and pull requests welcome!
