# Textbuilder2e

Convert [Pathbuilder 2e](https://pathbuilder2e.com/) JSON exports to human-readable text formats.

## Features

- **Build format** (default): Level-by-level progression showing choices at each level
- **Static format**: Complete character sheet with final stats
- **Clipboard support**: Read JSON directly from clipboard (macOS)
- **Remaster compatible**: Uses ability modifiers (not scores), no alignment

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
# Build progression format (default)
textbuilder2e.py character.json

# Static character sheet
textbuilder2e.py character.json --static

# Read from clipboard, print to stdout
textbuilder2e.py -c --stdout

# Specify output file
textbuilder2e.py character.json -o mycharacter.txt
```

## Output Examples

See the [examples/](examples/) folder for sample output:
- `glimpse.json` - Pathbuilder 2e JSON export
- `glimpse-static.txt` - Static character sheet format
- `glimpse-build.txt` - Build progression format

### Header (both formats)
```
============================================================
  Glimpse, goblin xbowslinger (rogue) 12th
  STR +0  DEX +5  CON +4  INT +2  WIS +0  CHA +5
============================================================
```

### Static Format
Shows complete character sheet: basic info, defenses, saves, skills, feats, equipment.

### Build Format
Shows level-by-level progression: ancestry/background choices, class features, feat selections at each level, ability boosts.

## Options

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Output file (default: `<input>.txt`) |
| `-c`, `--clipboard` | Read JSON from clipboard (macOS) |
| `--static` | Use static character sheet format |
| `--stdout` | Print to stdout instead of file |
| `--no-prompt` | Skip interactive skill increase prompts |

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)

## License

MIT License - feel free to use, modify, and share.

## Contributing

Issues and pull requests welcome!
