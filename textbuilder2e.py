#!/usr/bin/env python3
"""
Textbuilder2e - Convert Pathbuilder 2e JSON exports to human-readable text.

Usage:
    python textbuilder2e.py <json_file>                 # Default (build) template
    python textbuilder2e.py <json_file> -t static       # Static character sheet
    python textbuilder2e.py <json_file> -t condensed    # Condensed format
    python textbuilder2e.py -c --stdout                 # Read from clipboard, print to stdout

Templates:
    build (default)  Level-by-level progression showing choices at each level
    static           Complete character sheet with all stats and features
    condensed        Compact format: just feats grouped by type, no levels shown
"""

import argparse
import json
import subprocess
import sys
import textwrap
from pathlib import Path


# NOTE: Direct fetching from pathbuilder2e.com is not possible.
# The API at https://pathbuilder2e.com/json.php?id={ID} is protected by
# Cloudflare bot protection which requires JavaScript execution.
# Users must export JSON manually from the Pathbuilder app/website:
#   Menu -> Export Character -> Export to Foundry VTT (JSON)


# Class feature level mappings
# Maps (class, feature_name) or just feature_name to the level it's gained
CLASS_FEATURE_LEVELS = {
    # Commander class features
    ("Commander", "Tactics"): 1,
    ("Commander", "Commander's Banner"): 1,
    ("Commander", "Warfare Expertise"): 1,
    ("Commander", "Military Expertise"): 1,
    ("Commander", "Drilled Reactions"): 3,
    ("Commander", "Weapon Expertise"): 5,
    ("Commander", "Expert Tactician"): 7,
    ("Commander", "Weapon Specialization"): 7,
    ("Commander", "Strategic Expertise"): 9,
    ("Commander", "Greater Weapon Specialization"): 15,
    ("Commander", "Tactical Mastery"): 17,
    ("Commander", "Legendary Tactician"): 19,

    # Generic features shared across classes
    "Weapon Specialization": 7,
    "Greater Weapon Specialization": 15,
    "Resolve": 9,
    "Evasion": 7,
    "Vigilant Senses": 7,
    "Weapon Expertise": 5,
    "Armor Expertise": 11,
    "Light Armor Expertise": 13,
    "Weapon Mastery": 13,
}

# Tactics (Commander) - all gained at level 1
COMMANDER_TACTICS = {
    "Gather to Me!", "Reload!", "Defensive Retreat", "Strike Hard!",
    "Bolster Defenses", "Lead the Charge", "Pin Down", "Pincer Attack",
    "Protective Screen", "Alley-Oop", "Coordinated Assault",
}


def get_feature_level(char_class: str, feature_name: str) -> int:
    """Get the level a class feature is gained at.

    Returns the level or 1 if unknown (defaults to showing at level 1).
    """
    # Check class-specific mapping first
    if (char_class, feature_name) in CLASS_FEATURE_LEVELS:
        return CLASS_FEATURE_LEVELS[(char_class, feature_name)]

    # Check Commander tactics (all level 1)
    if char_class == "Commander" and feature_name in COMMANDER_TACTICS:
        return 1

    # Check generic mappings
    if feature_name in CLASS_FEATURE_LEVELS:
        return CLASS_FEATURE_LEVELS[feature_name]

    # Default to level 1
    return 1


def get_modifier(score: int) -> int:
    """Calculate ability modifier from ability score."""
    return (score - 10) // 2


def format_modifier(mod: int) -> str:
    """Format modifier with +/- sign."""
    return f"+{mod}" if mod >= 0 else str(mod)


def proficiency_rank(level: int) -> str:
    """Convert proficiency number to rank name."""
    ranks = {0: "Untrained", 2: "Trained", 4: "Expert", 6: "Master", 8: "Legendary"}
    return ranks.get(level, f"Unknown ({level})")


def format_spells_section(spell_casters: list) -> list:
    """Format spellcasting section for character sheet.

    Returns list of lines to add to output.
    """
    if not spell_casters:
        return []

    # Filter out empty spellcasters (no spells known)
    active_casters = []
    for caster in spell_casters:
        spells = caster.get("spells", [])
        has_spells = any(s.get("list", []) for s in spells)
        if has_spells:
            active_casters.append(caster)

    if not active_casters:
        return []

    lines = []
    lines.append("SPELLS")
    lines.append("-" * 40)

    for caster in active_casters:
        name = caster.get("name", "Unknown")
        tradition = caster.get("magicTradition", "").capitalize()
        cast_type = caster.get("spellcastingType", "").capitalize()
        innate = caster.get("innate", False)
        per_day = caster.get("perDay", [])

        # Header for this spellcaster
        caster_info = f"{name}"
        if tradition:
            caster_info += f" ({tradition}"
            if cast_type and not innate:
                caster_info += f", {cast_type}"
            if innate:
                caster_info += ", Innate"
            caster_info += ")"
        lines.append(f"  {caster_info}")

        # Spells by level
        spells = caster.get("spells", [])
        for spell_entry in spells:
            spell_level = spell_entry.get("spellLevel", 0)
            spell_list = spell_entry.get("list", [])
            if not spell_list:
                continue

            # Get slots for this level
            slots = per_day[spell_level] if spell_level < len(per_day) else 0

            if spell_level == 0:
                level_label = "Cantrips"
            else:
                level_label = f"Level {spell_level}"
                if slots > 0 and not innate:
                    level_label += f" ({slots}/day)"

            lines.append(f"    {level_label}: {', '.join(spell_list)}")

        lines.append("")

    return lines


def wrap_text(text: str, width: int = 71) -> str:
    """Word wrap text while preserving indentation.

    Each line's leading whitespace is detected and used as the indent
    for any wrapped continuation lines.

    For lines containing comma-separated lists, wraps at comma boundaries
    to keep list items intact.
    """
    if width <= 0:
        return text  # No wrapping

    lines = text.split('\n')
    wrapped_lines = []

    for line in lines:
        # Preserve empty lines and separator lines (===, ---)
        if not line.strip() or line.strip().startswith('=') or line.strip().startswith('-') and len(set(line.strip())) == 1:
            wrapped_lines.append(line)
            continue

        # Detect leading indentation
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]

        # If line fits, keep as-is
        if len(line) <= width:
            wrapped_lines.append(line)
            continue

        # Check if this is a comma-separated list (has multiple commas)
        if stripped.count(',') >= 2:
            # Wrap at comma boundaries to keep list items intact
            wrapped_lines.extend(_wrap_list_line(stripped, indent, width))
        else:
            # Standard word wrap for non-list content
            wrapper = textwrap.TextWrapper(
                width=width,
                initial_indent=indent,
                subsequent_indent=indent + "  ",
                break_long_words=False,
                break_on_hyphens=False
            )
            wrapped_lines.extend(wrapper.wrap(stripped))

    return '\n'.join(wrapped_lines)


def _wrap_list_line(content: str, indent: str, width: int) -> list:
    """Wrap a comma-separated list, keeping items intact."""
    # Check if line has a prefix like "Skills: " or "Ancestry: "
    if ': ' in content:
        prefix, rest = content.split(': ', 1)
        prefix = prefix + ': '
    else:
        prefix = ''
        rest = content

    items = [item.strip() for item in rest.split(',')]
    result_lines = []
    current_line = indent + prefix

    for i, item in enumerate(items):
        # Add comma except for last item
        item_with_comma = item + (',' if i < len(items) - 1 else '')

        # Check if adding this item would exceed width
        test_line = current_line + ('' if current_line.endswith(': ') or current_line == indent + prefix else ' ') + item_with_comma

        if len(test_line) <= width or current_line == indent + prefix:
            # Add to current line
            if current_line.endswith(': ') or current_line == indent + prefix:
                current_line += item_with_comma
            else:
                current_line += ' ' + item_with_comma
        else:
            # Start new line
            result_lines.append(current_line)
            current_line = indent + '  ' + item_with_comma  # Extra indent for continuation

    if current_line.strip():
        result_lines.append(current_line)

    return result_lines


def format_character_static(data: dict) -> str:
    """Convert Pathbuilder JSON to formatted text (static character sheet)."""
    build = data.get("build", data)
    lines = []

    # Header
    name = build.get("name", "Unknown Character")
    abilities = build.get("abilities", {})
    lines.append("=" * 60)
    lines.append(f"  {name}")
    # Ability modifiers on one line
    ability_mods = []
    for abbr in ["str", "dex", "con", "int", "wis", "cha"]:
        score = abilities.get(abbr, 10)
        mod = get_modifier(score)
        ability_mods.append(f"{abbr.upper()} {format_modifier(mod)}")
    lines.append("  " + "  ".join(ability_mods))
    lines.append("=" * 60)
    lines.append("")

    # Basic Info
    lines.append("BASIC INFORMATION")
    lines.append("-" * 40)
    lines.append(f"Class:      {build.get('class', 'Unknown')} {build.get('level', '?')}")
    if build.get("dualClass"):
        lines.append(f"Dual Class: {build['dualClass']}")
    lines.append(f"Ancestry:   {build.get('ancestry', 'Unknown')}")
    lines.append(f"Heritage:   {build.get('heritage', 'Unknown')}")
    lines.append(f"Background: {build.get('background', 'Unknown')}")
    lines.append(f"Size:       {build.get('sizeName', 'Medium')}")
    if build.get("deity") and build.get("deity") != "Not set":
        lines.append(f"Deity:      {build['deity']}")
    lines.append("")

    # Defenses
    attrs = build.get("attributes", {})
    profs = build.get("proficiencies", {})
    ac_info = build.get("acTotal", {})

    lines.append("DEFENSES")
    lines.append("-" * 40)

    # HP calculation
    ancestry_hp = attrs.get("ancestryhp", 0)
    class_hp = attrs.get("classhp", 0)
    level = build.get("level", 1)
    con_mod = get_modifier(abilities.get("con", 10))
    bonus_hp = attrs.get("bonushp", 0)
    bonus_per_level = attrs.get("bonushpPerLevel", 0)
    total_hp = ancestry_hp + (class_hp + con_mod + bonus_per_level) * level + bonus_hp
    lines.append(f"HP: {total_hp}")

    ac = ac_info.get("acTotal", 10)
    shield = ac_info.get("shieldBonus", 0)
    lines.append(f"AC: {ac}" + (f" ({ac + int(shield)} with shield)" if shield else ""))

    lines.append("")
    lines.append("Saving Throws:")
    for save, abbr in [("fortitude", "Fort"), ("reflex", "Ref"), ("will", "Will")]:
        prof = profs.get(save, 0)
        rank = proficiency_rank(prof)
        ability = {"fortitude": "con", "reflex": "dex", "will": "wis"}[save]
        ability_mod = get_modifier(abilities.get(ability, 10))
        total = prof + (level if prof > 0 else 0) + ability_mod
        lines.append(f"  {abbr}: {format_modifier(total)} ({rank})")

    lines.append("")
    perc_prof = profs.get("perception", 0)
    perc_mod = get_modifier(abilities.get("wis", 10))
    perc_total = perc_prof + (level if perc_prof > 0 else 0) + perc_mod
    lines.append(f"Perception: {format_modifier(perc_total)} ({proficiency_rank(perc_prof)})")

    # Speed
    speed = attrs.get("speed", 25) + attrs.get("speedBonus", 0)
    lines.append(f"Speed: {speed} ft")
    lines.append("")

    # Skills
    lines.append("SKILLS")
    lines.append("-" * 40)
    skill_abilities = {
        "acrobatics": "dex", "arcana": "int", "athletics": "str",
        "crafting": "int", "deception": "cha", "diplomacy": "cha",
        "intimidation": "cha", "medicine": "wis", "nature": "wis",
        "occultism": "int", "performance": "cha", "religion": "wis",
        "society": "int", "stealth": "dex", "survival": "wis", "thievery": "dex"
    }

    trained_skills = []
    for skill, ability in skill_abilities.items():
        prof = profs.get(skill, 0)
        if prof > 0:
            ability_mod = get_modifier(abilities.get(ability, 10))
            total = prof + level + ability_mod
            trained_skills.append((skill.capitalize(), total, proficiency_rank(prof)))

    for skill, total, rank in sorted(trained_skills, key=lambda x: x[0]):
        lines.append(f"  {skill}: {format_modifier(total)} ({rank})")

    # Lores
    lores = build.get("lores", [])
    if lores:
        lines.append("")
        lines.append("Lore Skills:")
        int_mod = get_modifier(abilities.get("int", 10))
        for lore in lores:
            lore_name = lore[0] if isinstance(lore, list) else lore
            lore_prof = lore[1] if isinstance(lore, list) and len(lore) > 1 else 2
            total = lore_prof + level + int_mod
            lines.append(f"  {lore_name} Lore: {format_modifier(total)} ({proficiency_rank(lore_prof)})")
    lines.append("")

    # Class Features
    specials = build.get("specials", [])
    if specials:
        lines.append("CLASS FEATURES")
        lines.append("-" * 40)
        for special in specials:
            lines.append(f"  - {special}")
        lines.append("")

    # Spells
    spell_casters = build.get("spellCasters", [])
    spell_lines = format_spells_section(spell_casters)
    if spell_lines:
        lines.extend(spell_lines)

    # Feats
    feats = build.get("feats", [])
    if feats:
        lines.append("FEATS")
        lines.append("-" * 40)

        feat_groups = {}
        for feat in feats:
            feat_name = feat[0] if isinstance(feat, list) else feat
            feat_note = feat[1] if isinstance(feat, list) and len(feat) > 1 and feat[1] else None
            feat_type = feat[2] if isinstance(feat, list) and len(feat) > 2 else "Other"
            feat_level = feat[3] if isinstance(feat, list) and len(feat) > 3 else "?"

            if feat_type not in feat_groups:
                feat_groups[feat_type] = []

            display = feat_name
            if feat_note:
                display += f" ({feat_note})"
            feat_groups[feat_type].append((feat_level, display))

        for feat_type in ["Heritage", "Ancestry Feat", "Class Feat", "Archetype Feat",
                          "Skill Feat", "General Feat", "Awarded Feat"]:
            if feat_type in feat_groups:
                lines.append(f"  {feat_type}s:" if not feat_type.endswith("Feat") else f"  {feat_type}s:")
                for lvl, name in sorted(feat_groups[feat_type], key=lambda x: (x[0] if isinstance(x[0], int) else 0)):
                    lines.append(f"    Lvl {lvl}: {name}")

        for feat_type, feat_list in feat_groups.items():
            if feat_type not in ["Heritage", "Ancestry Feat", "Class Feat", "Archetype Feat",
                                  "Skill Feat", "General Feat", "Awarded Feat"]:
                lines.append(f"  {feat_type}:")
                for lvl, name in sorted(feat_list, key=lambda x: (x[0] if isinstance(x[0], int) else 0)):
                    lines.append(f"    Lvl {lvl}: {name}")
        lines.append("")

    # Weapons
    weapons = build.get("weapons", [])
    if weapons:
        lines.append("WEAPONS")
        lines.append("-" * 40)
        for weapon in weapons:
            display = weapon.get("display", weapon.get("name", "Unknown"))
            attack = weapon.get("attack", 0)
            die = weapon.get("die", "d4")
            damage_type = weapon.get("damageType", "")
            damage_bonus = weapon.get("damageBonus", 0)
            striking = weapon.get("str", "")

            num_dice = 1
            if striking == "striking":
                num_dice = 2
            elif striking == "greaterStriking":
                num_dice = 3
            elif striking == "majorStriking":
                num_dice = 4

            damage_str = f"{num_dice}{die}"
            if damage_bonus:
                damage_str += f"+{damage_bonus}" if damage_bonus > 0 else str(damage_bonus)
            damage_str += f" {damage_type}"

            lines.append(f"  {display}")
            lines.append(f"    Attack: {format_modifier(attack)}, Damage: {damage_str}")
        lines.append("")

    # Armor
    armor = build.get("armor", [])
    if armor:
        lines.append("ARMOR & SHIELDS")
        lines.append("-" * 40)
        for piece in armor:
            display = piece.get("display") or piece.get("name", "Unknown")
            worn = piece.get("worn", False)
            lines.append(f"  {display}" + (" (worn)" if worn else ""))
        lines.append("")

    # Equipment
    equipment = build.get("equipment", [])
    if equipment:
        lines.append("EQUIPMENT")
        lines.append("-" * 40)
        for item in equipment:
            if isinstance(item, list):
                name = item[0]
                qty = item[1] if len(item) > 1 else 1
                note = item[2] if len(item) > 2 else ""
                display = name
                if qty > 1:
                    display += f" x{qty}"
                if note:
                    display += f" ({note})"
                lines.append(f"  - {display}")
            else:
                lines.append(f"  - {item}")
        lines.append("")

    # Money
    money = build.get("money", {})
    if any(money.values()):
        lines.append("MONEY")
        lines.append("-" * 40)
        coins = []
        for coin, abbr in [("pp", "pp"), ("gp", "gp"), ("sp", "sp"), ("cp", "cp")]:
            if money.get(coin, 0) > 0:
                coins.append(f"{money[coin]} {abbr}")
        lines.append("  " + ", ".join(coins) if coins else "  None")
        lines.append("")

    # Animal Companions / Pets
    pets = build.get("pets", [])
    if pets:
        lines.append("ANIMAL COMPANIONS")
        lines.append("-" * 40)
        for pet in pets:
            name = pet.get("name", "Unknown")
            animal = pet.get("animal", "")
            pet_type = pet.get("type", "")
            mature = pet.get("mature", False)
            incredible = pet.get("incredible", False)
            specializations = pet.get("specializations", [])

            display = name
            if animal and animal != name:
                display += f" ({animal})"
            if mature:
                display += " [Mature]"
            if incredible:
                inc_type = pet.get("incredibleType", "")
                display += f" [Incredible - {inc_type}]" if inc_type else " [Incredible]"

            lines.append(f"  {display}")
            if specializations:
                lines.append(f"    Specializations: {', '.join(specializations)}")
        lines.append("")

    # Familiars
    familiars = build.get("familiars", [])
    if familiars:
        lines.append("FAMILIARS")
        lines.append("-" * 40)
        for familiar in familiars:
            name = familiar.get("name", "Unknown")
            abilities = familiar.get("abilities", [])
            lines.append(f"  {name}")
            if abilities:
                lines.append(f"    Abilities: {', '.join(abilities)}")
        lines.append("")

    # Languages
    languages = build.get("languages", [])
    if languages and languages != ["None selected"]:
        lines.append("LANGUAGES")
        lines.append("-" * 40)
        lines.append("  " + ", ".join(languages))
        lines.append("")

    return "\n".join(lines)


def format_character_condensed(data: dict) -> str:
    """Convert Pathbuilder JSON to condensed text format.

    Condensed format omits:
    - Class features (everyone can look these up)
    - Level numbers on feats
    - Equipment/weapons

    Just shows the key choices: ancestry, class, background, and feats by type.
    """
    build = data.get("build", data)
    lines = []

    # Header
    name = build.get("name", "Unknown Character")
    abilities = build.get("abilities", {})
    lines.append("=" * 60)
    lines.append(f"  {name}")
    # Ability modifiers on one line
    ability_mods = []
    for abbr in ["str", "dex", "con", "int", "wis", "cha"]:
        score = abilities.get(abbr, 10)
        mod = get_modifier(score)
        ability_mods.append(f"{abbr.upper()} {format_modifier(mod)}")
    lines.append("  " + "  ".join(ability_mods))
    lines.append("=" * 60)
    lines.append("")

    # Basic Info (condensed)
    char_class = build.get('class', 'Unknown')
    level = build.get('level', '?')
    ancestry = build.get('ancestry', 'Unknown')
    heritage = build.get('heritage', 'Unknown')
    background = build.get('background', 'Unknown')

    lines.append(f"{ancestry} ({heritage}) {char_class} {level}")
    lines.append(f"Background: {background}")
    if build.get("dualClass"):
        lines.append(f"Dual Class: {build['dualClass']}")
    lines.append("")

    # Defenses (condensed)
    attrs = build.get("attributes", {})
    profs = build.get("proficiencies", {})
    ac_info = build.get("acTotal", {})

    # HP calculation
    ancestry_hp = attrs.get("ancestryhp", 0)
    class_hp = attrs.get("classhp", 0)
    con_mod = get_modifier(abilities.get("con", 10))
    bonus_hp = attrs.get("bonushp", 0)
    bonus_per_level = attrs.get("bonushpPerLevel", 0)
    total_hp = ancestry_hp + (class_hp + con_mod + bonus_per_level) * level + bonus_hp

    ac = ac_info.get("acTotal", 10)

    # Saves on one line
    saves = []
    for save, abbr in [("fortitude", "Fort"), ("reflex", "Ref"), ("will", "Will")]:
        prof = profs.get(save, 0)
        ability = {"fortitude": "con", "reflex": "dex", "will": "wis"}[save]
        ability_mod = get_modifier(abilities.get(ability, 10))
        total = prof + (level if prof > 0 else 0) + ability_mod
        saves.append(f"{abbr} {format_modifier(total)}")

    perc_prof = profs.get("perception", 0)
    perc_mod = get_modifier(abilities.get("wis", 10))
    perc_total = perc_prof + (level if perc_prof > 0 else 0) + perc_mod

    lines.append(f"HP {total_hp}  AC {ac}  {' '.join(saves)}  Per {format_modifier(perc_total)}")
    lines.append("")

    # Skills (condensed - just trained+)
    skill_abilities = {
        "acrobatics": "dex", "arcana": "int", "athletics": "str",
        "crafting": "int", "deception": "cha", "diplomacy": "cha",
        "intimidation": "cha", "medicine": "wis", "nature": "wis",
        "occultism": "int", "performance": "cha", "religion": "wis",
        "society": "int", "stealth": "dex", "survival": "wis", "thievery": "dex"
    }

    trained_skills = []
    for skill, ability in skill_abilities.items():
        prof = profs.get(skill, 0)
        if prof > 0:
            ability_mod = get_modifier(abilities.get(ability, 10))
            total = prof + level + ability_mod
            rank_abbr = {2: "T", 4: "E", 6: "M", 8: "L"}.get(prof, "?")
            trained_skills.append(f"{skill.capitalize()} {format_modifier(total)}({rank_abbr})")

    # Lores
    lores = build.get("lores", [])
    int_mod = get_modifier(abilities.get("int", 10))
    for lore in lores:
        lore_name = lore[0] if isinstance(lore, list) else lore
        lore_prof = lore[1] if isinstance(lore, list) and len(lore) > 1 else 2
        total = lore_prof + level + int_mod
        rank_abbr = {2: "T", 4: "E", 6: "M", 8: "L"}.get(lore_prof, "?")
        trained_skills.append(f"{lore_name} Lore {format_modifier(total)}({rank_abbr})")

    lines.append("Skills: " + ", ".join(sorted(trained_skills)))
    lines.append("")

    # Feats - grouped by type, with level in parens
    feats = build.get("feats", [])
    if feats:
        lines.append("FEATS")
        lines.append("-" * 40)

        feat_groups = {}
        seen_feats = {}  # Track feat names to avoid duplicates
        for feat in feats:
            feat_name = feat[0] if isinstance(feat, list) else feat
            feat_note = feat[1] if isinstance(feat, list) and len(feat) > 1 and feat[1] else None
            feat_type = feat[2] if isinstance(feat, list) and len(feat) > 2 else "Other"
            feat_level = feat[3] if isinstance(feat, list) and len(feat) > 3 else "?"

            # Normalize feat type names
            if feat_type == "Heritage":
                continue  # Skip heritage, it's shown in basic info

            # Group similar types
            if feat_type in ["Ancestry Feat"]:
                group = "Ancestry"
            elif feat_type in ["Class Feat"]:
                group = "Class"
            elif feat_type in ["Skill Feat"]:
                group = "Skill"
            elif feat_type in ["General Feat"]:
                group = "General"
            elif feat_type in ["Archetype Feat"]:
                group = "Archetype"
            else:
                group = feat_type

            if group not in feat_groups:
                feat_groups[group] = []
                seen_feats[group] = set()

            # Build display with level
            display = feat_name
            if feat_note:
                display += f" [{feat_note}]"
            display += f" ({feat_level})"

            if feat_name not in seen_feats[group]:  # Avoid duplicates by name
                feat_groups[group].append(display)
                seen_feats[group].add(feat_name)

        # Output in preferred order
        for group in ["Ancestry", "Class", "Archetype", "Skill", "General", "Awarded Feat"]:
            if group in feat_groups:
                lines.append(f"  {group}: {', '.join(feat_groups[group])}")

        # Any remaining groups
        for group, feat_list in feat_groups.items():
            if group not in ["Ancestry", "Class", "Archetype", "Skill", "General", "Awarded Feat"]:
                lines.append(f"  {group}: {', '.join(feat_list)}")

        lines.append("")

    return "\n".join(lines)


def format_post_reddit(data: dict) -> str:
    """Format character for Reddit post (markdown)."""
    build = data.get("build", data)
    abilities = build.get("abilities", {})

    name = build.get("name", "Unknown")
    char_class = build.get("class", "Unknown")
    level = build.get("level", "?")
    ancestry = build.get("ancestry", "Unknown")
    heritage = build.get("heritage", "Unknown")
    background = build.get("background", "Unknown")

    # Ability mods
    mods = []
    for abbr in ["str", "dex", "con", "int", "wis", "cha"]:
        score = abilities.get(abbr, 10)
        mod = get_modifier(score)
        mods.append(f"{abbr.upper()} {format_modifier(mod)}")

    lines = []
    lines.append(f"**{name}**")
    lines.append(f"{ancestry} ({heritage}) {char_class} {level}")
    lines.append(f"Background: {background}")
    lines.append(f"`{' | '.join(mods)}`")

    # Feats grouped by type
    feats = build.get("feats", [])
    if feats:
        feat_groups = {}
        for feat in feats:
            feat_name = feat[0] if isinstance(feat, list) else feat
            feat_type = feat[2] if isinstance(feat, list) and len(feat) > 2 else "Other"
            feat_level = feat[3] if isinstance(feat, list) and len(feat) > 3 else "?"

            if feat_type == "Heritage":
                continue

            if feat_type in ["Ancestry Feat"]:
                group = "Ancestry"
            elif feat_type in ["Class Feat"]:
                group = "Class"
            elif feat_type in ["Skill Feat"]:
                group = "Skill"
            elif feat_type in ["General Feat"]:
                group = "General"
            elif feat_type in ["Archetype Feat"]:
                group = "Archetype"
            else:
                group = feat_type

            if group not in feat_groups:
                feat_groups[group] = []
            feat_groups[group].append(f"{feat_name} ({feat_level})")

        for group in ["Ancestry", "Class", "Archetype", "Skill", "General"]:
            if group in feat_groups:
                lines.append(f"**{group}:** {', '.join(feat_groups[group])}")

        for group, feat_list in feat_groups.items():
            if group not in ["Ancestry", "Class", "Archetype", "Skill", "General"]:
                lines.append(f"**{group}:** {', '.join(feat_list)}")

    # Reddit markdown needs double newlines for line breaks
    return "\n\n".join(lines)


def format_post_bluesky(data: dict) -> str:
    """Format character for Bluesky post (compact, ~300 char limit)."""
    build = data.get("build", data)
    abilities = build.get("abilities", {})

    name = build.get("name", "Unknown")
    char_class = build.get("class", "Unknown")
    level = build.get("level", "?")
    ancestry = build.get("ancestry", "Unknown")

    # Compact ability mods
    mods = []
    for abbr in ["str", "dex", "con", "int", "wis", "cha"]:
        score = abilities.get(abbr, 10)
        mod = get_modifier(score)
        mods.append(f"{abbr[0].upper()}{format_modifier(mod)}")

    lines = []
    lines.append(f"{name}")
    lines.append(f"{ancestry} {char_class} {level}")
    lines.append(" ".join(mods))

    # Just list key feats compactly
    feats = build.get("feats", [])
    class_feats = []
    for feat in feats:
        feat_name = feat[0] if isinstance(feat, list) else feat
        feat_type = feat[2] if isinstance(feat, list) and len(feat) > 2 else ""
        if feat_type == "Class Feat":
            class_feats.append(feat_name)

    if class_feats:
        lines.append(f"Class: {', '.join(class_feats[:5])}")  # Limit to 5

    return "\n".join(lines)


def get_skill_increase_levels(char_class: str, char_level: int) -> list:
    """Return list of levels where this class gets skill increases."""
    if char_class == "Rogue":
        # Rogues get skill increases at every level starting at 2
        return list(range(2, char_level + 1))
    else:
        # Most classes get skill increases at odd levels starting at 3
        return [lvl for lvl in [3, 5, 7, 9, 11, 13, 15, 17, 19] if lvl <= char_level]


def get_int_skill_training_levels(abilities: dict, char_level: int) -> list:
    """Return list of levels where INT modifier increases, granting new trained skills.

    When a character's INT modifier increases, they gain a new trained skill.
    This typically happens when INT goes from odd to even (e.g., 11->12, 13->14).
    """
    breakdown = abilities.get("breakdown", {})
    boosts = breakdown.get("mapLevelledBoosts", {})

    # Calculate starting INT from ancestry/background/class boosts at level 1
    int_score = 10
    for boost_list in [breakdown.get("ancestryBoosts", []),
                       breakdown.get("ancestryFree", []),
                       breakdown.get("backgroundBoosts", []),
                       breakdown.get("classBoosts", [])]:
        if "Int" in boost_list:
            int_score += 2

    # Also check level 1 boosts
    if "1" in boosts and "Int" in boosts["1"]:
        int_score += 2

    # Track levels where INT modifier increases
    int_training_levels = []
    prev_mod = (int_score - 10) // 2

    for lvl in range(2, char_level + 1):
        lvl_str = str(lvl)
        if lvl_str in boosts and "Int" in boosts[lvl_str]:
            int_score += 2
            new_mod = (int_score - 10) // 2
            if new_mod > prev_mod:
                int_training_levels.append(lvl)
                prev_mod = new_mod

    return int_training_levels


def prompt_skill_training_and_increases(char_class: str, char_level: int, profs: dict, abilities: dict) -> tuple:
    """Interactively prompt user for skill increases and INT-based skill training.

    Returns:
        tuple: (skill_increases dict, int_skill_training dict)
    """
    skill_list = [
        "acrobatics", "arcana", "athletics", "crafting", "deception", "diplomacy",
        "intimidation", "medicine", "nature", "occultism", "performance", "religion",
        "society", "stealth", "survival", "thievery"
    ]

    skill_increase_levels = get_skill_increase_levels(char_class, char_level)
    int_training_levels = get_int_skill_training_levels(abilities, char_level)

    skill_increases = {}
    int_skill_training = {}

    # Get trained skills (eligible for increases)
    trained_skills = [s.capitalize() for s in skill_list if profs.get(s, 0) >= 2]
    # Get all skills for INT training selection
    all_skills = [s.capitalize() for s in skill_list]

    # Prompt for INT-based skill training first
    if int_training_levels:
        print(f"\n--- INT-Based Skill Training ---")
        print(f"Your INT modifier increased at these levels, granting new trained skills.")
        print(f"All skills: {', '.join(sorted(all_skills))}")
        print()

        for lvl in int_training_levels:
            while True:
                choice = input(f"Level {lvl} new trained skill from INT (or 'skip'): ").strip()
                if choice.lower() == 'skip' or choice == '':
                    int_skill_training[lvl] = None
                    break
                choice_normalized = choice.capitalize()
                if choice_normalized in all_skills:
                    int_skill_training[lvl] = choice_normalized
                    break
                else:
                    print(f"  '{choice}' not a valid skill. Try again.")

    # Prompt for skill increases
    if skill_increase_levels:
        print(f"\n--- Skill Increase Selection ---")
        print(f"Trained skills: {', '.join(sorted(trained_skills))}")
        print()

        for lvl in skill_increase_levels:
            while True:
                choice = input(f"Level {lvl} skill increase (or 'skip'): ").strip()
                if choice.lower() == 'skip' or choice == '':
                    skill_increases[lvl] = None
                    break
                choice_normalized = choice.capitalize()
                if choice_normalized in trained_skills:
                    skill_increases[lvl] = choice_normalized
                    break
                else:
                    print(f"  '{choice}' not found in trained skills. Try again.")

    return skill_increases, int_skill_training


def prompt_skill_increases(char_class: str, char_level: int, profs: dict, abilities: dict, level: int) -> dict:
    """Legacy function - redirects to combined prompt."""
    skill_increases, _ = prompt_skill_training_and_increases(char_class, char_level, profs, abilities)
    return skill_increases


def prompt_class_feature_levels(char_class: str, char_level: int, specials: list, heritage: str) -> dict:
    """Interactively prompt user for class feature levels.

    Returns:
        dict: Maps feature name to level gained
    """
    # Filter out ancestry/heritage features that shouldn't be prompted
    ancestry_features = {heritage, "Darkvision", "Low-Light Vision"}

    # Filter out subclass identifiers
    subclass_keywords = ["Racket", "Doctrine", "Muse", "Bloodline", "Order",
                         "Methodology", "Way", "Cause", "Tactics"]

    features_to_prompt = []
    for special in specials:
        # Skip ancestry features
        if special in ancestry_features:
            continue
        # Skip subclass identifiers
        if any(kw in special for kw in subclass_keywords):
            continue
        # Check if we already know the level from our mapping
        if (char_class, special) in CLASS_FEATURE_LEVELS:
            continue
        if special in CLASS_FEATURE_LEVELS:
            continue
        if char_class == "Commander" and special in COMMANDER_TACTICS:
            continue
        # This feature needs a level assignment
        features_to_prompt.append(special)

    if not features_to_prompt:
        return {}

    feature_levels = {}

    print(f"\n--- Class Feature Levels ---")
    print(f"The following {char_class} features need level assignments.")
    print(f"Enter the level (1-{char_level}) when each feature was gained, or 'skip'.")
    print()

    for feature in features_to_prompt:
        while True:
            choice = input(f"  {feature} (level 1-{char_level}, or 'skip'): ").strip()
            if choice.lower() == 'skip' or choice == '':
                feature_levels[feature] = 1  # Default to level 1
                break
            try:
                lvl = int(choice)
                if 1 <= lvl <= char_level:
                    feature_levels[feature] = lvl
                    break
                else:
                    print(f"    Level must be between 1 and {char_level}.")
            except ValueError:
                print(f"    Enter a number or 'skip'.")

    return feature_levels


def format_character_build(data: dict, skill_increases: dict = None, int_skill_training: dict = None, feature_levels: dict = None) -> str:
    """Convert Pathbuilder JSON to build progression format."""
    build = data.get("build", data)
    lines = []

    char_class = build.get("class", "Unknown")
    ancestry = build.get("ancestry", "Unknown")
    heritage = build.get("heritage", "Unknown")
    background = build.get("background", "Unknown")
    key_ability = build.get("keyability", "").upper()
    char_level = build.get("level", 1)

    # Extract ability breakdown
    abilities = build.get("abilities", {})

    # Header
    name = build.get("name", "Unknown Character")
    lines.append("=" * 60)
    lines.append(f"  {name}")
    # Ability modifiers on one line
    ability_mods = []
    for abbr in ["str", "dex", "con", "int", "wis", "cha"]:
        score = abilities.get(abbr, 10)
        mod = get_modifier(score)
        ability_mods.append(f"{abbr.upper()} {format_modifier(mod)}")
    lines.append("  " + "  ".join(ability_mods))
    lines.append("  CHARACTER BUILD PROGRESSION")
    lines.append("=" * 60)
    lines.append("")
    breakdown = abilities.get("breakdown", {})
    ancestry_boosts = breakdown.get("ancestryBoosts", [])
    ancestry_free = breakdown.get("ancestryFree", [])
    ancestry_flaws = breakdown.get("ancestryFlaws", [])
    background_boosts = breakdown.get("backgroundBoosts", [])
    class_boosts = breakdown.get("classBoosts", [])
    levelled_boosts = breakdown.get("mapLevelledBoosts", {})

    # Extract feats by level
    feats = build.get("feats", [])
    feats_by_level = {}
    for feat in feats:
        if isinstance(feat, list) and len(feat) >= 4:
            feat_name = feat[0]
            feat_note = feat[1] if feat[1] else None
            feat_type = feat[2]
            feat_level = feat[3]

            if feat_level not in feats_by_level:
                feats_by_level[feat_level] = []

            display = feat_name
            if feat_note:
                display += f" ({feat_note})"
            feats_by_level[feat_level].append((feat_type, display))

    # Extract lores (from background, level 1)
    lores = build.get("lores", [])

    # Extract proficiencies
    profs = build.get("proficiencies", {})
    attrs = build.get("attributes", {})
    ac_info = build.get("acTotal", {})

    skill_abilities = {
        "acrobatics": "dex", "arcana": "int", "athletics": "str",
        "crafting": "int", "deception": "cha", "diplomacy": "cha",
        "intimidation": "cha", "medicine": "wis", "nature": "wis",
        "occultism": "int", "performance": "cha", "religion": "wis",
        "society": "int", "stealth": "dex", "survival": "wis", "thievery": "dex"
    }

    # Specials (class features)
    specials = build.get("specials", [])
    subclass_features = [s for s in specials if "Racket" in s or "Doctrine" in s or
                         "Muse" in s or "Bloodline" in s or "Order" in s or
                         "Methodology" in s or "Way" in s or "Cause" in s or
                         "Tactics" in s]

    # Group class features by level
    features_by_level = {}
    heritage_name = build.get("heritage", "")
    ancestry_features = {heritage_name, "Darkvision", "Low-Light Vision"}
    for special in specials:
        # Skip ancestry/heritage features
        if special in ancestry_features or special in subclass_features:
            continue
        # Check user-provided levels first, then fall back to mapping
        if feature_levels and special in feature_levels:
            feat_level = feature_levels[special]
        else:
            feat_level = get_feature_level(char_class, special)
        if feat_level not in features_by_level:
            features_by_level[feat_level] = []
        features_by_level[feat_level].append(special)

    # =====================
    # ANCESTRY & BACKGROUND
    # =====================
    lines.append("ANCESTRY & BACKGROUND")
    lines.append("-" * 40)
    lines.append(f"Ancestry: {ancestry}")
    lines.append(f"Heritage: {heritage}")
    if ancestry_boosts:
        lines.append(f"  Ancestry Boosts: {', '.join(ancestry_boosts)}")
    if ancestry_free:
        lines.append(f"  Free Boost: {', '.join(ancestry_free)}")
    if ancestry_flaws:
        lines.append(f"  Ancestry Flaw: {', '.join(ancestry_flaws)}")
    lines.append("")
    lines.append(f"Background: {background}")
    if background_boosts:
        lines.append(f"  Background Boosts: {', '.join(background_boosts)}")
    if lores:
        for lore in lores:
            lore_name = lore[0] if isinstance(lore, list) else lore
            lines.append(f"  Lore: {lore_name}")
    lines.append("")

    # =====================
    # CLASS
    # =====================
    lines.append("CLASS")
    lines.append("-" * 40)
    lines.append(f"Class: {char_class}")
    if key_ability:
        lines.append(f"  Key Ability: {key_ability}")
    if class_boosts:
        lines.append(f"  Class Boost: {', '.join(class_boosts)}")
    if subclass_features:
        lines.append(f"  Subclass: {subclass_features[0]}")
    lines.append("")

    # =====================
    # DEFENSE
    # =====================
    lines.append("DEFENSE")
    lines.append("-" * 40)

    # HP calculation
    ancestry_hp = attrs.get("ancestryhp", 0)
    class_hp = attrs.get("classhp", 0)
    con_mod = get_modifier(abilities.get("con", 10))
    bonus_hp = attrs.get("bonushp", 0)
    bonus_per_level = attrs.get("bonushpPerLevel", 0)
    total_hp = ancestry_hp + (class_hp + con_mod + bonus_per_level) * char_level + bonus_hp
    lines.append(f"HP: {total_hp}")

    ac = ac_info.get("acTotal", 10)
    shield = ac_info.get("shieldBonus", 0)
    lines.append(f"AC: {ac}" + (f" ({ac + int(shield)} with shield)" if shield else ""))

    lines.append("")
    lines.append("Saving Throws:")
    for save, abbr in [("fortitude", "Fort"), ("reflex", "Ref"), ("will", "Will")]:
        prof = profs.get(save, 0)
        rank = proficiency_rank(prof)
        ability = {"fortitude": "con", "reflex": "dex", "will": "wis"}[save]
        ability_mod = get_modifier(abilities.get(ability, 10))
        total = prof + (char_level if prof > 0 else 0) + ability_mod
        lines.append(f"  {abbr}: {format_modifier(total)} ({rank})")

    lines.append("")
    perc_prof = profs.get("perception", 0)
    perc_mod = get_modifier(abilities.get("wis", 10))
    perc_total = perc_prof + (char_level if perc_prof > 0 else 0) + perc_mod
    lines.append(f"Perception: {format_modifier(perc_total)} ({proficiency_rank(perc_prof)})")

    speed = attrs.get("speed", 25) + attrs.get("speedBonus", 0)
    lines.append(f"Speed: {speed} ft")
    lines.append("")

    # =====================
    # OFFENSE
    # =====================
    weapons = build.get("weapons", [])
    if weapons:
        lines.append("OFFENSE")
        lines.append("-" * 40)
        for weapon in weapons:
            display = weapon.get("display", weapon.get("name", "Unknown"))
            attack = weapon.get("attack", 0)
            die = weapon.get("die", "d4")
            damage_type = weapon.get("damageType", "")
            damage_bonus = weapon.get("damageBonus", 0)
            striking = weapon.get("str", "")

            num_dice = 1
            if striking == "striking":
                num_dice = 2
            elif striking == "greaterStriking":
                num_dice = 3
            elif striking == "majorStriking":
                num_dice = 4

            damage_str = f"{num_dice}{die}"
            if damage_bonus:
                damage_str += f"+{damage_bonus}" if damage_bonus > 0 else str(damage_bonus)
            damage_str += f" {damage_type}"

            lines.append(f"  {display}: {format_modifier(attack)} / {damage_str}")
        lines.append("")

    # =====================
    # SKILLS
    # =====================
    lines.append("SKILLS")
    lines.append("-" * 40)

    trained_skills = []
    for skill, ability in skill_abilities.items():
        prof = profs.get(skill, 0)
        if prof > 0:
            ability_mod = get_modifier(abilities.get(ability, 10))
            total = prof + char_level + ability_mod
            trained_skills.append((skill.capitalize(), total, proficiency_rank(prof)))

    for skill, total, rank in sorted(trained_skills, key=lambda x: x[0]):
        lines.append(f"  {skill}: {format_modifier(total)} ({rank})")

    # Lores
    if lores:
        lines.append("")
        lines.append("Lore Skills:")
        int_mod = get_modifier(abilities.get("int", 10))
        for lore in lores:
            lore_name = lore[0] if isinstance(lore, list) else lore
            lore_prof = lore[1] if isinstance(lore, list) and len(lore) > 1 else 2
            total = lore_prof + char_level + int_mod
            lines.append(f"  {lore_name} Lore: {format_modifier(total)} ({proficiency_rank(lore_prof)})")
    lines.append("")

    # =====================
    # SPELLS (for spellcasters)
    # =====================
    spell_casters = build.get("spellCasters", [])
    spell_lines = format_spells_section(spell_casters)
    if spell_lines:
        lines.extend(spell_lines)

    # Focus spells
    focus = build.get("focus", {})
    focus_points = build.get("focusPoints", 0)
    if focus and focus_points > 0:
        lines.append("FOCUS SPELLS")
        lines.append("-" * 40)
        lines.append(f"  Focus Points: {focus_points}")
        for tradition, abilities_dict in focus.items():
            for ability, details in abilities_dict.items():
                cantrips = details.get("focusCantrips", [])
                spells = details.get("focusSpells", [])
                if cantrips:
                    lines.append(f"  Focus Cantrips ({tradition.capitalize()}): {', '.join(cantrips)}")
                if spells:
                    lines.append(f"  Focus Spells ({tradition.capitalize()}): {', '.join(spells)}")
        lines.append("")

    # =====================
    # COMPANIONS & FAMILIARS
    # =====================
    pets = build.get("pets", [])
    familiars = build.get("familiars", [])

    if pets:
        lines.append("ANIMAL COMPANIONS")
        lines.append("-" * 40)
        for pet in pets:
            name = pet.get("name", "Unknown")
            animal = pet.get("animal", "")
            mature = pet.get("mature", False)
            incredible = pet.get("incredible", False)

            display = name
            if animal and animal != name:
                display += f" ({animal})"
            if mature:
                display += " [Mature]"
            if incredible:
                inc_type = pet.get("incredibleType", "")
                display += f" [Incredible - {inc_type}]" if inc_type else " [Incredible]"

            lines.append(f"  {display}")
            specializations = pet.get("specializations", [])
            if specializations:
                lines.append(f"    Specializations: {', '.join(specializations)}")
        lines.append("")

    if familiars:
        lines.append("FAMILIARS")
        lines.append("-" * 40)
        for familiar in familiars:
            name = familiar.get("name", "Unknown")
            fam_abilities = familiar.get("abilities", [])
            lines.append(f"  {name}")
            if fam_abilities:
                lines.append(f"    Abilities: {', '.join(fam_abilities)}")
        lines.append("")

    # =====================
    # LEVEL BY LEVEL
    # =====================
    lines.append("LEVEL PROGRESSION")
    lines.append("=" * 40)

    skill_increase_levels = get_skill_increase_levels(char_class, char_level)
    int_training_levels = get_int_skill_training_levels(abilities, char_level)

    for lvl in range(1, char_level + 1):
        lines.append("")
        lines.append(f"LEVEL {lvl}")
        lines.append("-" * 20)

        level_content = []

        # Ability boosts at levels 1, 5, 10, 15, 20
        lvl_str = str(lvl)
        if lvl_str in levelled_boosts and levelled_boosts[lvl_str]:
            boosts = levelled_boosts[lvl_str]
            level_content.append(f"  Ability Boosts: {', '.join(boosts)}")

        # INT-based skill training (when INT modifier increases)
        if lvl in int_training_levels:
            if int_skill_training and lvl in int_skill_training and int_skill_training[lvl]:
                level_content.append(f"  Skill Training (INT): {int_skill_training[lvl]}")
            else:
                level_content.append("  Skill Training (INT): ___")

        # Feats at this level
        if lvl in feats_by_level:
            for feat_type, feat_name in feats_by_level[lvl]:
                if feat_type == "Awarded Feat":
                    # Mark awarded feats with asterisk
                    level_content.append(f"  {feat_name}*")
                else:
                    # Clean up feat type display
                    type_display = feat_type.replace(" Feat", "")
                    level_content.append(f"  {type_display}: {feat_name}")

        # Class features at this level
        if lvl in features_by_level:
            level_features = features_by_level[lvl]
            if level_features:
                level_content.append(f"  Class Features: {', '.join(level_features)}")

        # Skill increases
        if lvl in skill_increase_levels:
            if skill_increases and lvl in skill_increases and skill_increases[lvl]:
                level_content.append(f"  Skill Increase: {skill_increases[lvl]}")
            else:
                level_content.append("  Skill Increase: ___")

        if level_content:
            lines.extend(level_content)
        else:
            lines.append("  (No selections)")

    lines.append("")
    lines.append("* = Granted by ancestry, heritage, or background")
    lines.append("")

    return "\n".join(lines)


def read_from_clipboard() -> str:
    """Read text from clipboard using pbpaste (macOS)."""
    try:
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except FileNotFoundError:
        print("Error: pbpaste not found. This option is macOS only.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error reading clipboard: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Convert Pathbuilder 2e JSON exports to human-readable text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Templates:
  build (default)  Level-by-level progression showing choices at each level
  static           Complete character sheet with all stats and features
  condensed        Compact format: feats grouped by type, no levels shown

Examples:
  %(prog)s character.json                 Output to character-build.txt
  %(prog)s character.json -t static       Output to character-static.txt
  %(prog)s character.json -t condensed    Output to character-condensed.txt
  %(prog)s -c --stdout                    Read from clipboard, print to stdout
"""
    )

    parser.add_argument("input", nargs="?", help="Input JSON file")
    parser.add_argument("-t", "--template", choices=["build", "static", "condensed"],
                        default="build", help="Output template (default: build)")
    parser.add_argument("-p", "--post", choices=["reddit", "bluesky"],
                        help="Format for social media post (overrides --template)")
    parser.add_argument("-w", "--width", type=int, default=71,
                        help="Line width for word wrap (default: 71, 0 to disable)")
    parser.add_argument("-o", "--output", help="Output file (default: <input>-<template>.txt)")
    parser.add_argument("-c", "--clipboard", action="store_true",
                        help="Read JSON from clipboard (macOS)")
    parser.add_argument("--stdout", action="store_true",
                        help="Print to stdout instead of file")
    parser.add_argument("--no-prompt", action="store_true",
                        help="Skip interactive prompts for class features and skills (build only)")

    args = parser.parse_args()

    # Validate arguments
    if not args.clipboard and not args.input:
        parser.print_help()
        sys.exit(1)

    # Load JSON
    input_path = None

    if args.clipboard:
        clipboard_content = read_from_clipboard()
        try:
            data = json.loads(clipboard_content)
        except json.JSONDecodeError as e:
            print(f"Error: Clipboard does not contain valid JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: File not found: {input_path}", file=sys.stderr)
            sys.exit(1)
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    # Format character based on post format or template
    if args.post == "reddit":
        formatted = format_post_reddit(data)
    elif args.post == "bluesky":
        formatted = format_post_bluesky(data)
    elif args.template == "static":
        formatted = format_character_static(data)
    elif args.template == "condensed":
        formatted = format_character_condensed(data)
    else:
        # Build template - get prompts interactively unless --no-prompt
        skill_increases = None
        int_skill_training = None
        feature_levels = None
        if not args.no_prompt:
            build = data.get("build", data)
            char_class = build.get("class", "Unknown")
            char_level = build.get("level", 1)
            profs = build.get("proficiencies", {})
            abilities = build.get("abilities", {})
            specials = build.get("specials", [])
            heritage = build.get("heritage", "")
            # Prompt for class feature levels first
            feature_levels = prompt_class_feature_levels(
                char_class, char_level, specials, heritage)
            # Then skill training/increases
            skill_increases, int_skill_training = prompt_skill_training_and_increases(
                char_class, char_level, profs, abilities)
        formatted = format_character_build(data, skill_increases, int_skill_training, feature_levels)

    # Apply word wrap (skip for post formats - platforms handle their own wrapping)
    if not args.post:
        formatted = wrap_text(formatted, args.width)

    # Determine output destination
    if args.stdout or (args.clipboard and not args.output):
        print(formatted)
    else:
        if args.output:
            output_path = Path(args.output)
        elif input_path:
            # Include template/post format in filename: name-build.txt, name-static.txt, etc.
            format_name = args.post if args.post else args.template
            output_path = input_path.parent / f"{input_path.stem}-{format_name}.txt"
        else:
            print(formatted)
            return

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(formatted)
        print(f"Output written to: {output_path}")


if __name__ == "__main__":
    main()
