"""
MIL-DTL-22759 / SAE AS22759 hookup-wire chooser.

Harness build instructions import this module, not the generator. A later
loop library_utils.pull()s every cable that has lib_repo set.

    import sys
    sys.path.append("/absolute/path/to/M22759")
    import M22759

    for instance in instances_list.read():
        if instance.get("item_type") != "harness_cable":
            continue
        spec = instance.get("wire_spec") or instance.get("component_wire") or ""
        if "22759" not in spec.upper():
            continue
        instances_list.modify(
            instance.get("instance_name"),
            {
                "mpn": M22759.choose_part(
                    slash=instance.get("slash") or spec,
                    gauge=instance.get("gauge"),
                    color=instance.get("color") or "white",
                ),
                "lib_repo": "https://github.com/harnice/harnice-aerospace-library",
                "lib_subpath": "M22759",
            },
        )

Official PIN uses a slash (M22759/11-22-9). The library PN replaces that
slash with an underscore so the folder name is filesystem-safe
(M22759_11-22-9_A). Pass return_divider="/" to get the official spelling.
"""

import re


# ---------------------------------------------------------------------------
# How-to-order
# ---------------------------------------------------------------------------
# Official anatomy, Glenair M22759 Wires catalog "HOW TO ORDER":
#   https://www.glenair.com/wire-and-cable/m22759-wires/pdf/m22759-wires.pdf
#   M22759 / {slash} - {AWG} - {base}{stripe1}{stripe2}{stripe3}
# Sample: M22759/11-24-9012  ->  slash 11, 24 AWG, white with black/brown/red
# stripes.
#
# Color digits are MIL-STD-681 (Glenair Table II on the same page, and on
# every GS22759-* slash-sheet PDF). Glenair note 6: the base (jacket) color
# must be white (9) when stripes are added. Up to three stripes. Stripe
# combinations beyond the preferred single-tracer set are factory / custom
# and are not generated; is_legal_color_code() still describes the spec rule.
#
# This library stocks the six slash sheets that have published finished-wire
# diameter, resistance and weight tables in the sources cited on SLASH_SHEETS.
# Other AS22759 slashes exist (Glenair Table I lists dozens) but are omitted
# until those dimensions are transcribed.
#
# M27500 Table I symbols that use these slashes as the component wire:
#   RC=/11  TE=/16  TG=/18  SB=/32  SC=/33
# /41 is not a current M27500 basic-wire symbol in this repo.

# MIL-STD-681 / Glenair Table II.
# https://www.glenair.com/wire-and-cable/m22759-wires/pdf/m22759-wires.pdf
COLOR_DIGITS = {
    "0": "black",
    "1": "brown",
    "2": "red",
    "3": "orange",
    "4": "yellow",
    "5": "green",
    "6": "blue",
    "7": "violet",
    "8": "gray",
    "9": "white",
}

# Solid 0-9 plus the preferred white-base single-tracer set (90-98). Those
# nine striped codes are the airframe identification colors used as the
# preferred method on MIL-DTL-27500 Table III A (white wire, colored stripe).
LIBRARY_COLOR_CODES = tuple("0123456789") + tuple(f"9{d}" for d in "012345678")

_COLOR_NAME_TO_DIGIT = {
    "black": "0",
    "blk": "0",
    "bk": "0",
    "brown": "1",
    "brn": "1",
    "bn": "1",
    "red": "2",
    "rd": "2",
    "orange": "3",
    "org": "3",
    "or": "3",
    "yellow": "4",
    "yel": "4",
    "ye": "4",
    "green": "5",
    "grn": "5",
    "gn": "5",
    "blue": "6",
    "blu": "6",
    "be": "6",
    "violet": "7",
    "vio": "7",
    "vt": "7",
    "purple": "7",
    "gray": "8",
    "grey": "8",
    "gry": "8",
    "gy": "8",
    "white": "9",
    "wht": "9",
    "wh": "9",
}

# Standard MIL stranding (number of strands x strand AWG). Glenair Table III
# on the family how-to-order page, restated on every GS22759-* slash sheet.
# https://www.glenair.com/wire-and-cable/m22759-wires/pdf/m22759-wires.pdf
#
# NOTE: the Glenair M22759 wires catalog prints "19 x 25" for 12 AWG on /11,
# /16 and /18. SAE AS22759/16 and /18 and the Amphenol catalog both give
# 37 x 28, which is the standard MIL stranding, so 37x28 is used here — same
# judgment as M27500/m27500_generator.py.
STRANDING = {
    30: "7x38",
    28: "7x36",
    26: "19x38",
    24: "19x36",
    22: "19x34",
    20: "19x32",
    18: "19x30",
    16: "19x29",
    14: "19x27",
    12: "37x28",
    10: "37x26",
    8: "133x29",
}

# AS29606 stranded-conductor diameter, inches. Midpoint of the min/max
# columns on Glenair GS22759-32 Table I (30-12 AWG) and GS22759-41 Table I
# (10 and 8 AWG). Same stranding is used on every copper slash sheet here.
# https://www.glenair.com/wire-and-cable/pdf/mil-star/gs22759-32.pdf
# https://www.glenair.com/wire-and-cable/pdf/mil-star/gs22759-41.pdf
CONDUCTOR_DIA_IN = {
    30: 0.0120,  # 0.0105-0.0134
    28: 0.0150,  # 0.0135-0.0164
    26: 0.0190,  # 0.0175-0.0204
    24: 0.0240,  # 0.0225-0.0254
    22: 0.0300,  # 0.0285-0.0314
    20: 0.0380,  # 0.0365-0.0394
    18: 0.0475,  # 0.0455-0.0494
    16: 0.0535,  # 0.0515-0.0554
    14: 0.0670,  # 0.0645-0.0694
    12: 0.0865,  # 0.0835-0.0894
    10: 0.1095,  # 0.106-0.113
    8: 0.1655,  # 0.158-0.173
}

# MIL-DTL-27500 Table I basic-wire symbols whose component wire is one of
# these slash sheets. /41 has no symbol in the current M27500 family.
M27500_SYMBOL_TO_SLASH = {
    "RC": 11,
    "TE": 16,
    "TG": 18,
    "SB": 32,
    "SC": 33,
}
SLASH_TO_M27500_SYMBOL = {slash: symbol for symbol, slash in M27500_SYMBOL_TO_SLASH.items()}


# ---------------------------------------------------------------------------
# Slash sheets this library stocks
# ---------------------------------------------------------------------------
# Each row is one commercially published construction. `wire_od_in`,
# `resistance_ohm_per_kft` and `weight_lb_per_kft` are slash-sheet maxima /
# nominals from the URL on `datasheet`. A gauge is only legal if it appears
# in `wire_od_in`.
#
# /32 temperature: Glenair's family Table I sometimes prints 200 C; the
# construction-specific GS22759-32 sheet (notes 4) is 150 C and is the source
# used here, matching M27500.
SLASH_SHEETS = {
    11: {
        "spec": "MIL-DTL-22759/11",
        "insulation": "PTFE",
        "insulation_detail": "extruded PTFE, medium weight",
        "wall": "medium",
        "conductor": "copper",
        "plating": "silver",
        "conductor_material": "silver-coated copper",
        "temperature_c": 200,
        "voltage_v": 600,
        "datasheet": "https://www.ryanelectronics.com/products/m2275911/",
        "weight_source": (
            "M22759/11 slash-sheet max weight, lbs/1000 ft "
            "(Glenair M22759 wires / Ryan Electronics, "
            "https://www.ryanelectronics.com/products/m2275911/)"
        ),
        # Finished wire OD, inches. Glenair M22759 wires / Ryan Electronics.
        "wire_od_in": {
            28: 0.033,
            26: 0.038,
            24: 0.043,
            22: 0.049,
            20: 0.058,
            18: 0.068,
            16: 0.075,
            14: 0.090,
            12: 0.111,
            10: 0.139,
            8: 0.202,
        },
        "resistance_ohm_per_kft": {
            28: 63.8,
            26: 38.4,
            24: 24.3,
            22: 15.1,
            20: 9.19,
            18: 5.79,
            16: 4.52,
            14: 2.88,
            12: 1.81,
            10: 1.19,
            8: 0.658,
        },
        "weight_lb_per_kft": {
            28: 1.36,
            26: 1.90,
            24: 2.58,
            22: 3.72,
            20: 5.43,
            18: 8.14,
            16: 10.0,
            14: 15.1,
            12: 24.1,
            10: 37.8,
            8: 65.5,
        },
    },
    16: {
        "spec": "MIL-DTL-22759/16",
        "insulation": "ETFE",
        "insulation_detail": "extruded ETFE, medium wall",
        "wall": "medium",
        "conductor": "copper",
        "plating": "tin",
        "conductor_material": "tin-coated copper",
        "temperature_c": 150,
        "voltage_v": 600,
        "datasheet": "https://cdn.glenair.com/wire-and-cable/pdf/b/m22759-16.pdf",
        "weight_source": (
            "M22759/16 slash-sheet max weight, lbs/1000 ft "
            "(Glenair, https://cdn.glenair.com/wire-and-cable/pdf/b/m22759-16.pdf)"
        ),
        "wire_od_in": {
            24: 0.045,
            22: 0.052,
            20: 0.060,
            18: 0.071,
            16: 0.079,
            14: 0.093,
            12: 0.114,
            10: 0.139,
            8: 0.199,
        },
        "resistance_ohm_per_kft": {
            24: 26.2,
            22: 16.2,
            20: 9.88,
            18: 6.23,
            16: 4.81,
            14: 3.06,
            12: 2.02,
            10: 1.26,
            8: 0.701,
        },
        "weight_lb_per_kft": {
            24: 2.57,
            22: 3.68,
            20: 5.36,
            18: 7.89,
            16: 9.95,
            14: 14.9,
            12: 22.6,
            10: 35.1,
            8: 63.5,
        },
    },
    18: {
        "spec": "MIL-DTL-22759/18",
        "insulation": "ETFE",
        "insulation_detail": "extruded ETFE, thin wall",
        "wall": "thin",
        "conductor": "copper",
        "plating": "tin",
        "conductor_material": "tin-coated copper",
        "temperature_c": 150,
        "voltage_v": 600,
        "datasheet": (
            "https://www.glenair.com/wire-and-cable/m22759-wires/pdf/m22759-wires.pdf"
        ),
        "weight_source": (
            "M22759/18 slash-sheet max weight, lbs/1000 ft "
            "(Glenair M22759 wires catalog, "
            "https://www.glenair.com/wire-and-cable/m22759-wires/pdf/m22759-wires.pdf)"
        ),
        "wire_od_in": {
            26: 0.032,
            24: 0.036,
            22: 0.043,
            20: 0.051,
            18: 0.061,
            16: 0.070,
            14: 0.085,
            12: 0.107,
            10: 0.134,
        },
        "resistance_ohm_per_kft": {
            26: 41.3,
            24: 26.2,
            22: 16.2,
            20: 9.88,
            18: 6.23,
            16: 4.81,
            14: 3.06,
            12: 2.02,
            10: 1.26,
        },
        "weight_lb_per_kft": {
            26: 1.45,
            24: 2.09,
            22: 3.05,
            20: 4.58,
            18: 6.92,
            16: 8.75,
            14: 13.7,
            12: 21.0,
            10: 33.1,
        },
    },
    32: {
        "spec": "MIL-DTL-22759/32",
        "insulation": "XL-ETFE",
        "insulation_detail": "crosslinked modified ETFE, light wall",
        "wall": "light",
        "conductor": "copper",
        "plating": "tin",
        "conductor_material": "tin-coated copper",
        "temperature_c": 150,
        "voltage_v": 600,
        "datasheet": "https://www.glenair.com/wire-and-cable/pdf/mil-star/gs22759-32.pdf",
        "weight_source": (
            "M22759/32 slash-sheet max weight, lbs/1000 ft "
            "(Glenair GS22759-32, "
            "https://www.glenair.com/wire-and-cable/pdf/mil-star/gs22759-32.pdf)"
        ),
        "wire_od_in": {
            30: 0.024,
            28: 0.027,
            26: 0.032,
            24: 0.037,
            22: 0.043,
            20: 0.050,
            18: 0.060,
            16: 0.068,
            14: 0.085,
            12: 0.103,
        },
        "resistance_ohm_per_kft": {
            30: 108.4,
            28: 68.6,
            26: 41.3,
            24: 26.2,
            22: 16.2,
            20: 9.88,
            18: 6.23,
            16: 4.81,
            14: 3.06,
            12: 2.02,
        },
        "weight_lb_per_kft": {
            30: 0.66,
            28: 0.91,
            26: 1.40,
            24: 2.00,
            22: 2.80,
            20: 4.30,
            18: 6.50,
            16: 8.30,
            14: 13.00,
            12: 19.70,
        },
    },
    33: {
        "spec": "MIL-DTL-22759/33",
        "insulation": "XL-ETFE",
        "insulation_detail": "crosslinked modified ETFE",
        "wall": "light",
        "conductor": "high-strength copper alloy",
        "plating": "silver",
        "conductor_material": "silver-coated high-strength copper alloy",
        "temperature_c": 200,
        "voltage_v": 600,
        "datasheet": (
            "https://www.glenair.com/guardian-conduit-system/pdf/"
            "wire-diameter-lookup-tables.pdf"
        ),
        "weight_source": (
            "M22759/33 slash-sheet weight, lbs/1000 ft "
            "(Glenair wire-diameter lookup tables, "
            "https://www.glenair.com/guardian-conduit-system/pdf/"
            "wire-diameter-lookup-tables.pdf)"
        ),
        "wire_od_in": {
            30: 0.024,
            28: 0.027,
            26: 0.032,
            24: 0.037,
            22: 0.043,
            20: 0.050,
        },
        "resistance_ohm_per_kft": {
            30: 117.4,
            28: 74.4,
            26: 44.8,
            24: 28.4,
            22: 17.5,
            20: 10.7,
        },
        "weight_lb_per_kft": {
            30: 0.67,
            28: 0.93,
            26: 1.43,
            24: 2.04,
            22: 2.96,
            20: 4.49,
        },
    },
    41: {
        "spec": "MIL-DTL-22759/41",
        "insulation": "XL-ETFE",
        # Dual wall commercially (primary + jacket). Tables give finished OD
        # only, so the product is still modeled as one insulated conductor.
        "insulation_detail": "crosslinked modified ETFE, dual wall",
        "wall": "dual",
        "conductor": "copper",
        "plating": "nickel",
        "conductor_material": "nickel-coated copper",
        "temperature_c": 200,
        "voltage_v": 600,
        "datasheet": "https://www.glenair.com/wire-and-cable/pdf/mil-star/gs22759-41.pdf",
        "weight_source": (
            "M22759/41 slash-sheet max weight, lbs/1000 ft "
            "(Glenair GS22759-41, "
            "https://www.glenair.com/wire-and-cable/pdf/mil-star/gs22759-41.pdf)"
        ),
        "wire_od_in": {
            26: 0.040,
            24: 0.045,
            22: 0.050,
            20: 0.058,
            18: 0.070,
            16: 0.077,
            14: 0.094,
            12: 0.111,
            10: 0.134,
            8: 0.195,
        },
        "resistance_ohm_per_kft": {
            26: 42.2,
            24: 25.9,
            22: 16.0,
            20: 9.77,
            18: 6.10,
            16: 4.76,
            14: 3.00,
            12: 1.98,
            10: 1.24,
            8: 0.694,
        },
        "weight_lb_per_kft": {
            26: 1.7,
            24: 2.3,
            22: 3.2,
            20: 4.7,
            18: 7.2,
            16: 9.0,
            14: 13.8,
            12: 20.5,
            10: 32.4,
            8: 67.4,
        },
    },
}

HOW_TO_ORDER_URL = (
    "https://www.glenair.com/wire-and-cable/m22759-wires/pdf/m22759-wires.pdf"
)

_INSULATION_ALIASES = {
    "PTFE": "PTFE",
    "TFE": "PTFE",
    "TFEZEL": "ETFE",
    "ETFE": "ETFE",
    "XLETFE": "XL-ETFE",
    "XL-ETFE": "XL-ETFE",
    "XL_ETFE": "XL-ETFE",
    "CROSSLINKED ETFE": "XL-ETFE",
    "CROSSLINKED MODIFIED ETFE": "XL-ETFE",
}

_PLATING_ALIASES = {
    "SILVER": "silver",
    "AG": "silver",
    "SPC": "silver",
    "SILVER-COATED": "silver",
    "TIN": "tin",
    "SN": "tin",
    "TPC": "tin",
    "TIN-COATED": "tin",
    "NICKEL": "nickel",
    "NI": "nickel",
    "NPC": "nickel",
    "NICKEL-COATED": "nickel",
}

_CONDUCTOR_ALIASES = {
    "COPPER": "copper",
    "CU": "copper",
    "HIGH-STRENGTH COPPER ALLOY": "high-strength copper alloy",
    "HIGH STRENGTH COPPER ALLOY": "high-strength copper alloy",
    "HS COPPER ALLOY": "high-strength copper alloy",
    "HSCA": "high-strength copper alloy",
    "HIGH-STRENGTH": "high-strength copper alloy",
}

_WALL_ALIASES = {
    "MEDIUM": "medium",
    "MEDIUM WEIGHT": "medium",
    "MEDIUM WALL": "medium",
    "THIN": "thin",
    "THIN WALL": "thin",
    "LIGHT": "light",
    "LIGHT WEIGHT": "light",
    "LIGHT WALL": "light",
    "LIGHTWEIGHT": "light",
    "DUAL": "dual",
    "DUAL WALL": "dual",
}

_PN_RE = re.compile(
    r"^M22759[/_](?P<slash>\d{1,3})-(?P<gauge>\d{1,4})-(?P<color>\d{1,4})$"
)


def list_slash_sheets():
    """Return the slash-sheet numbers this library stocks, sorted."""
    return sorted(SLASH_SHEETS)


def list_gauges(slash=None):
    """Return legal AWG sizes, optionally restricted to one slash sheet."""
    if slash is None:
        gauges = set()
        for spec in SLASH_SHEETS.values():
            gauges.update(spec["wire_od_in"])
        return sorted(gauges, reverse=True)
    spec = _require_slash(slash)
    return sorted(spec["wire_od_in"], reverse=True)


def list_colors():
    """Return the color codes this library emits (digits, preferred set)."""
    return list(LIBRARY_COLOR_CODES)


def list_part_numbers(return_divider=None):
    """Return every library PN the generator emits."""
    return [make_part_number(cfg, return_divider) for cfg in iter_part_configurations()]


def color_name(color_code):
    """Return the MIL-STD-681 color designation for a digit string, e.g. 90 -> white/black."""
    code = _require_library_color(color_code)
    return "/".join(COLOR_DIGITS[digit] for digit in code)


def color_names(color_code):
    """Return the list of color names in a code (base first, then stripes)."""
    code = _require_library_color(color_code)
    return [COLOR_DIGITS[digit] for digit in code]


def is_legal_color_code(color_code):
    """True if the digits are a spec-legal MIL-STD-681 code (not necessarily stocked).

    Solids are 0-9. Striped codes are 2-4 digits whose first digit is 9
    (Glenair note 6: white base required for stripes).
    """
    code = str(color_code).strip()
    if not code or not code.isdigit() or len(code) > 4:
        return False
    if any(digit not in COLOR_DIGITS for digit in code):
        return False
    if len(code) == 1:
        return True
    return code[0] == "9"


def is_legal_configuration(slash, gauge, color_code):
    """Return (True, None) if this library emits the SKU, else (False, reason)."""
    try:
        slash = _require_slash_number(slash)
    except ValueError as exc:
        return False, str(exc)
    spec = SLASH_SHEETS[slash]
    try:
        gauge = _normalize_gauge(gauge)
    except ValueError as exc:
        return False, str(exc)
    if gauge not in spec["wire_od_in"]:
        return False, (
            f"{spec['spec']} is not offered in {gauge} AWG in this library. "
            f"Legal gauges: {sorted(spec['wire_od_in'], reverse=True)}"
        )
    try:
        _require_library_color(color_code)
    except ValueError as exc:
        return False, str(exc)
    return True, None


def iter_part_configurations():
    """Yield one configuration dict per legal library SKU."""
    for slash in list_slash_sheets():
        spec = SLASH_SHEETS[slash]
        for gauge in sorted(spec["wire_od_in"], reverse=True):
            for color_code in LIBRARY_COLOR_CODES:
                yield {
                    "slash": slash,
                    "gauge": gauge,
                    "color": color_code,
                    "spec": spec,
                }


def make_part_number(cfg, return_divider=None):
    """Filesystem-safe library PN. Pass return_divider='/' for the official PIN."""
    divider = "_" if return_divider is None else str(return_divider)
    slash = _require_slash_number(cfg["slash"])
    gauge = _normalize_gauge(cfg["gauge"])
    color = _require_library_color(cfg["color"])
    return f"M22759{divider}{slash}-{gauge}-{color}"


def official_pin(cfg):
    """Official MIL / SAE spelling, e.g. M22759/11-22-9."""
    return make_part_number(cfg, return_divider="/")


def description_from_cfg(cfg):
    """ALL CAPS catalog sentence for the revision-history row."""
    slash = _require_slash_number(cfg["slash"])
    gauge = _normalize_gauge(cfg["gauge"])
    color = _require_library_color(cfg["color"])
    spec = SLASH_SHEETS[slash]
    color_words = color_name(color).replace("/", " / ").upper()
    return (
        f"CABLE, HOOKUP WIRE, {spec['spec']}, {gauge} AWG, "
        f"{STRANDING[gauge].upper()} {spec['conductor_material'].upper()}, "
        f"{spec['insulation_detail'].upper()}, "
        f"{spec['voltage_v']} V, {spec['temperature_c']} C, {color_words}"
    )


def parse_part_number(part_number):
    """Parse an official or library M22759 PN into slash / gauge / color fields."""
    pn = _normalize_pn_string(part_number)
    match = _PN_RE.match(pn)
    if not match:
        raise ValueError(
            f"Could not parse {part_number!r} as an M22759 part number. "
            "Expected M22759/{slash}-{AWG}-{color} "
            "(e.g. M22759/11-22-9 or M22759_11-22-9_A)."
        )
    slash = _require_slash_number(match.group("slash"))
    gauge = _normalize_gauge(match.group("gauge"))
    color = match.group("color")
    legal, reason = is_legal_configuration(slash, gauge, color)
    if not legal:
        raise ValueError(reason)
    spec = SLASH_SHEETS[slash]
    return {
        "slash": slash,
        "gauge": gauge,
        "color": color,
        "spec": spec,
        "insulation": spec["insulation"],
        "plating": spec["plating"],
        "conductor": spec["conductor"],
        "wall": spec["wall"],
        "temperature_c": spec["temperature_c"],
        "voltage_v": spec["voltage_v"],
    }


def choose_part(
    slash=None,
    gauge=None,
    color="9",
    insulation=None,
    plating=None,
    conductor=None,
    wall=None,
    temperature_c=None,
    voltage=None,
    m27500_symbol=None,
    part_number=None,
    return_divider=None,
):
    """
    Return a library M22759 PN that this family actually emits.

    Identify the slash sheet either by number (`slash=11`), by a full PN
    (`part_number="MS22759/11-22-9"`), by the M27500 basic-wire symbol
    (`m27500_symbol="TG"`), or by construction (`insulation`, `plating`,
    `conductor`, `wall`, `temperature_c`). Construction filters must resolve
    to exactly one stocked slash; otherwise ValueError lists the matches.

    `gauge` is required unless `part_number` already contains one.
    `color` accepts a digit code (9, 90), names (white, red), or a
    base/stripe designation (white/black).
    """
    if part_number is not None:
        parsed = parse_part_number(part_number)
        if slash is None:
            slash = parsed["slash"]
        if gauge is None:
            gauge = parsed["gauge"]
        if color in (None, "9") and parsed["color"] != "9":
            color = parsed["color"]
        elif color == "9":
            color = parsed["color"]

    if m27500_symbol is not None:
        symbol = str(m27500_symbol).strip().upper()
        if symbol not in M27500_SYMBOL_TO_SLASH:
            raise ValueError(
                f"Unknown M27500 basic-wire symbol {m27500_symbol!r}. "
                f"M22759 symbols in this library: {sorted(M27500_SYMBOL_TO_SLASH)}"
            )
        mapped = M27500_SYMBOL_TO_SLASH[symbol]
        if slash is not None and _require_slash_number(slash) != mapped:
            raise ValueError(
                f"m27500_symbol {symbol!r} is slash {mapped}, not {slash}."
            )
        slash = mapped

    if gauge is None:
        raise ValueError("choose_part requires gauge (AWG), e.g. gauge=22.")

    gauge = _normalize_gauge(gauge)
    color = normalize_color(color)
    slash = _resolve_slash(
        slash,
        gauge=gauge,
        insulation=insulation,
        plating=plating,
        conductor=conductor,
        wall=wall,
        temperature_c=temperature_c,
        voltage=voltage,
    )
    legal, reason = is_legal_configuration(slash, gauge, color)
    if not legal:
        raise ValueError(reason)
    return make_part_number(
        {"slash": slash, "gauge": gauge, "color": color},
        return_divider=return_divider,
    )


def normalize_color(color):
    """Accept a digit code, color name, or base/stripe designation. Return library digits."""
    if color is None:
        raise ValueError(
            "color is required. "
            f"Legal library codes: {', '.join(LIBRARY_COLOR_CODES)} "
            f"({', '.join(color_name(c) for c in LIBRARY_COLOR_CODES)})."
        )
    raw = str(color).strip().lower()
    if not raw:
        raise ValueError("color is empty.")

    compact_digits = raw.replace("-", "").replace("/", "").replace(" ", "").replace("_", "")
    if compact_digits.isdigit():
        return _require_library_color(compact_digits)

    tokens = [tok for tok in re.split(r"[/\-_,\s]+", raw) if tok]
    digits = []
    for token in tokens:
        if token in COLOR_DIGITS:
            digits.append(token)
            continue
        if token in _COLOR_NAME_TO_DIGIT:
            digits.append(_COLOR_NAME_TO_DIGIT[token])
            continue
        raise ValueError(
            f"Unknown color token {token!r} in {color!r}. "
            f"Expected a MIL-STD-681 digit 0-9 or name "
            f"({', '.join(COLOR_DIGITS[d] for d in '0123456789')})."
        )
    if not digits:
        raise ValueError(f"Could not read color {color!r}.")
    return _require_library_color("".join(digits))


def wire_od_in(slash, gauge):
    """Finished-wire outside diameter, inches, from the slash-sheet table."""
    spec = _require_slash(slash)
    gauge = _normalize_gauge(gauge)
    if gauge not in spec["wire_od_in"]:
        raise ValueError(
            f"{spec['spec']} is not offered in {gauge} AWG. "
            f"Legal: {sorted(spec['wire_od_in'], reverse=True)}"
        )
    return spec["wire_od_in"][gauge]


def conductor_od_in(gauge):
    """Stranded conductor diameter, inches (AS29606 midpoint)."""
    gauge = _normalize_gauge(gauge)
    if gauge not in CONDUCTOR_DIA_IN:
        raise ValueError(
            f"No AS29606 conductor diameter for {gauge} AWG in this library. "
            f"Legal: {sorted(CONDUCTOR_DIA_IN, reverse=True)}"
        )
    return CONDUCTOR_DIA_IN[gauge]


def insulation_wall_in(slash, gauge):
    """Radial insulation wall, inches: (finished OD - conductor OD) / 2.

    Derived from two datasheet columns, not a separate callout.
    """
    return (wire_od_in(slash, gauge) - conductor_od_in(gauge)) / 2.0


def m27500_symbol(slash):
    """Return the MIL-DTL-27500 Table I symbol for this slash, or None."""
    return SLASH_TO_M27500_SYMBOL.get(_require_slash_number(slash))


def _resolve_slash(
    slash,
    gauge,
    insulation,
    plating,
    conductor,
    wall,
    temperature_c,
    voltage,
):
    if slash is not None and not (
        insulation or plating or conductor or wall or temperature_c is not None or voltage is not None
    ):
        slash = _require_slash_number(slash)
        spec = SLASH_SHEETS[slash]
        if gauge not in spec["wire_od_in"]:
            raise ValueError(
                f"{spec['spec']} is not offered in {gauge} AWG. "
                f"Legal: {sorted(spec['wire_od_in'], reverse=True)}"
            )
        return slash

    matches = []
    for number, spec in SLASH_SHEETS.items():
        if gauge not in spec["wire_od_in"]:
            continue
        if slash is not None and number != _require_slash_number(slash):
            continue
        if insulation is not None and spec["insulation"] != _normalize_insulation(insulation):
            continue
        if plating is not None and spec["plating"] != _normalize_plating(plating):
            continue
        if conductor is not None and spec["conductor"] != _normalize_conductor(conductor):
            continue
        if wall is not None and spec["wall"] != _normalize_wall(wall):
            continue
        if temperature_c is not None and spec["temperature_c"] != int(temperature_c):
            continue
        if voltage is not None and spec["voltage_v"] != int(voltage):
            continue
        matches.append(number)

    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(
            "No stocked M22759 slash sheet matches "
            f"slash={slash!r}, gauge={gauge}, insulation={insulation!r}, "
            f"plating={plating!r}, conductor={conductor!r}, wall={wall!r}, "
            f"temperature_c={temperature_c!r}, voltage={voltage!r}. "
            f"Legal slashes: {list_slash_sheets()}."
        )
    raise ValueError(
        "Slash sheet is ambiguous. Matches: "
        + ", ".join(
            f"{n} ({SLASH_SHEETS[n]['insulation']}, {SLASH_SHEETS[n]['plating']}, "
            f"{SLASH_SHEETS[n]['wall']} wall, {SLASH_SHEETS[n]['temperature_c']} C)"
            for n in matches
        )
        + ". Pass slash= or add insulation / plating / wall / temperature_c."
    )


def _normalize_pn_string(part_number):
    text = str(part_number).strip().upper()
    text = text.replace(" ", "")
    for prefix in ("MIL-DTL-", "MIL-W-", "SAE-AS-", "SAE-AS", "SAEAS", "SAE"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    # MS / AS / GS / bare 22759 all collapse to the M22759 library prefix.
    if text.startswith(("MS22759", "AS22759", "GS22759")):
        text = "M22759" + text[7:]
    elif text.startswith("22759"):
        text = "M22759" + text[5:]
    # GS / some catalogs use all dashes: M22759-11-22-9
    if text.startswith("M22759-"):
        text = "M22759/" + text[len("M22759-") :]
    # Join optional extra stripe dashes: M22759/11-22-9-0-1-2 -> ...-9012
    match = re.match(r"^(M22759[/_]\d{1,3}-\d{1,4})-((?:\d-)*\d)$", text)
    if match:
        text = match.group(1) + "-" + match.group(2).replace("-", "")
    return text


def _require_slash_number(slash):
    if isinstance(slash, str):
        text = slash.strip().upper().replace(" ", "")
        # Allow passing a whole PN or "M22759/11" / "/11" as the slash argument.
        if "22759" in text or text.startswith("/"):
            digits = re.search(r"22759[/_-]?(\d{1,3})", text) or re.match(r"/(\d{1,3})$", text)
            if digits:
                text = digits.group(1)
        if not text.isdigit():
            raise ValueError(
                f"Unknown slash sheet {slash!r}. "
                f"Legal: {list_slash_sheets()}."
            )
        slash = int(text)
    else:
        slash = int(slash)
    if slash not in SLASH_SHEETS:
        raise ValueError(
            f"Slash sheet /{slash} is not in this library. "
            f"Legal: {list_slash_sheets()}."
        )
    return slash


def _require_slash(slash):
    return SLASH_SHEETS[_require_slash_number(slash)]


def _require_library_color(color_code):
    code = str(color_code).strip()
    if code not in LIBRARY_COLOR_CODES:
        if is_legal_color_code(code):
            raise ValueError(
                f"Color {color_code!r} is spec-legal but not stocked in this "
                f"library. Legal codes: {', '.join(LIBRARY_COLOR_CODES)}."
            )
        raise ValueError(
            f"Unknown color {color_code!r}. "
            f"Legal library codes: {', '.join(LIBRARY_COLOR_CODES)} "
            f"({', '.join(color_name(c) for c in LIBRARY_COLOR_CODES)})."
        )
    return code


def _normalize_gauge(gauge):
    if isinstance(gauge, str):
        text = gauge.strip().upper().replace(" ", "")
        text = text.replace("AWG", "").replace("GAUGE", "").replace("#", "")
        if not text.isdigit():
            raise ValueError(
                f"Could not read gauge {gauge!r}. Expected an AWG number, e.g. 22."
            )
        gauge = int(text)
    else:
        gauge = int(gauge)
    if gauge not in STRANDING:
        raise ValueError(
            f"Gauge {gauge} AWG is not in this library. "
            f"Legal: {sorted(STRANDING, reverse=True)}."
        )
    return gauge


def _normalize_insulation(value):
    key = str(value).strip().upper().replace("_", "-")
    if key not in _INSULATION_ALIASES:
        raise ValueError(
            f"Unknown insulation {value!r}. "
            f"Expected PTFE, ETFE, or XL-ETFE."
        )
    return _INSULATION_ALIASES[key]


def _normalize_plating(value):
    key = str(value).strip().upper().replace("_", "-")
    if key not in _PLATING_ALIASES:
        raise ValueError(
            f"Unknown plating {value!r}. Expected silver, tin, or nickel."
        )
    return _PLATING_ALIASES[key]


def _normalize_conductor(value):
    key = str(value).strip().upper().replace("_", " ")
    if key not in _CONDUCTOR_ALIASES:
        raise ValueError(
            f"Unknown conductor {value!r}. "
            "Expected copper or high-strength copper alloy."
        )
    return _CONDUCTOR_ALIASES[key]


def _normalize_wall(value):
    key = str(value).strip().upper().replace("_", " ")
    if key not in _WALL_ALIASES:
        raise ValueError(
            f"Unknown wall {value!r}. Expected medium, thin, light, or dual."
        )
    return _WALL_ALIASES[key]
