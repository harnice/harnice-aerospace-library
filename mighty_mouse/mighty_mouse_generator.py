import json
import math
import os
import subprocess
import sys

from harnice import state
from harnice.lists import rev_history


def _load_step_utils():
    try:
        from harnice.utils import step_utils as module
        return module
    except ImportError:
        pass
    import importlib.util

    sibling = os.path.normpath(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "Harnice",
            "src",
            "harnice",
            "utils",
            "step_utils.py",
        )
    )
    spec = importlib.util.spec_from_file_location("harnice_step_utils", sibling)
    if spec is None or spec.loader is None:
        raise ImportError(
            "Generating STEP envelopes requires harnice.utils.step_utils "
            "(Harnice src/harnice/utils/step_utils.py)."
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


step_utils = _load_step_utils()

REVISION = "1"
DATE_STARTED = "8/16/26"
delete_pngs = True

# ---------------------------------------------------------------------------
# Datasheet / catalog sources (traceability)
# ---------------------------------------------------------------------------
# Primary (how-to-order, shell styles 06/16, Table of A/B/C/D/E/F, notes):
#   Glenair Series 800 UN Thread Mating — 800-006 / 800-007 / 800-008 / 800-009
#   Plug with Hex or Knurled Coupling, Crimp Contacts, Banding Porch, or
#   Accessory Thread (U.S. CAGE 06324; sheet Rev. 04.29.24)
#   https://www.glenair.com/mighty-mouse/series-800-un-thread-mating/pdf/800-006-800-007-800-008-and-800-009.pdf
#
# Mouser-hosted copy of the Series 800 catalog:
#   https://www.mouser.com/datasheet/2/171/series800-190869.pdf
#
# Contact arrangements (mating face of pin insert shown):
#   https://www.glenair.com/mighty-mouse/series-800-un-thread-mating/pdf/contact-arrangements-mating-face-of-pin-insert-shown.pdf
#
# Specifications / materials and finishes:
#   https://www.glenair.com/mighty-mouse/series-800-un-thread-mating/pdf/specifications-materials-and-finishes.pdf
#
# Connector weights (Series 800 cable-plug maximum, grams):
#   https://www.glenair.com/mighty-mouse/series-800-un-thread-mating/pdf/connector-weights.pdf
#
# Coupling torque (Series 800 table):
#   https://www.glenair.com/mighty-mouse/pdf/general-information-and-reference/recommended-torque-and-demate-values.pdf
#
# Crimp tools / positioners:
#   https://www.glenair.com/mighty-mouse/contacts-and-tools/pdf/crimp-tools-and-positioners.pdf
#
# Band-Master ATS micro banding tool (integral band platform on 800-006):
#   https://www.glenair.com/mighty-mouse/accessories-backshells-and-tools/pdf/connector-holding-tools-and-band-master-ats-banding-tool/band-master-ats-shield-termination-tool-bands-and-instructions.pdf
# ---------------------------------------------------------------------------

# SVG px per inch — must match harnice part.py csys rendering (96 px/in)
PX_PER_IN = 96.0

# Origin is the right end of the banding knurl. The knurl itself extends −X
# so a terminated cable segment overlaps it. Overall length from the rear of
# the band porch to the connector face: Glenair drawing .850 (21.6) MAX.
# Banding platform length is not tabulated; 0.20 in is an estimate for
# drawing/csys silhouette only.
OVERALL_MAX_IN = 0.850
BAND_PLATFORM_IN = 0.20
BODY_IN = 0.65  # OVERALL_MAX_IN - BAND_PLATFORM_IN

SHELL_STYLES = {
    "06": "Standard Coupling Nut",
    "16": "Coupling Nut with Anti-Decoupling Wave Spring",
}

# How-to-order material / finish codes (Glenair 800-006 sheet).
FINISHES = {
    "C": "Aluminum / Black Anodize (Non-Conductive)",
    "M": "Aluminum / Electroless Nickel",
    "NF": "Aluminum / Cadmium with Olive Drab Chromate",
    "ZNU": "Aluminum / Zinc-Nickel with Black Chromate",
    "MT": "Aluminum / Nickel-PTFE",
    "Z1": "Stainless Steel / Passivated",
}

# Dimensions from Glenair 800-006/007/008/009 drawing, shell sizes 5–12.
# Style 06 = standard hex coupling nut; style 16 = wave-spring nut (larger A/B/C).
# D, E, F are shared. F accessory thread is listed on the sheet but is N/A on
# 800-006 (integral band platform, not accessory thread).
SHELL_DATA = {
    5: {
        "06": {"a_hex_in": 0.430, "b_in": 0.47, "c_in": 0.43},
        "16": {"a_hex_in": 0.495, "b_in": 0.54, "c_in": 0.49},
        "d_in": 0.230,
        "e_thread": ".3125-28 UN-2B",
        "f_thread": ".250-32 UNEF-2A",
    },
    6: {
        "06": {"a_hex_in": 0.500, "b_in": 0.55, "c_in": 0.50},
        "16": {"a_hex_in": 0.563, "b_in": 0.62, "c_in": 0.56},
        "d_in": 0.286,
        "e_thread": ".3750-28 UN-2B",
        "f_thread": ".3125-32 UNEF-2A",
    },
    7: {
        "06": {"a_hex_in": 0.625, "b_in": 0.68, "c_in": 0.62},
        "16": {"a_hex_in": 0.720, "b_in": 0.80, "c_in": 0.68},
        "d_in": 0.390,
        "e_thread": ".4375-28 UNEF-2B",
        "f_thread": ".4375-28 UNEF-2A",
    },
    8: {
        "06": {"a_hex_in": 0.680, "b_in": 0.75, "c_in": 0.68},
        "16": {"a_hex_in": 0.743, "b_in": 0.83, "c_in": 0.75},
        "d_in": 0.445,
        "e_thread": ".5000-32 UN-2B",
        "f_thread": ".5000-28 UNEF-2A",
    },
    9: {
        "06": {"a_hex_in": 0.750, "b_in": 0.83, "c_in": 0.75},
        "16": {"a_hex_in": 0.813, "b_in": 0.89, "c_in": 0.81},
        "d_in": 0.500,
        "e_thread": ".5625-32 UN-2B",
        "f_thread": ".5625-24 UNEF-2A",
    },
    10: {
        "06": {"a_hex_in": 0.812, "b_in": 0.90, "c_in": 0.81},
        "16": {"a_hex_in": 0.875, "b_in": 0.96, "c_in": 0.88},
        "d_in": 0.565,
        "e_thread": ".6250-32 UN-2B",
        "f_thread": ".6250-24 UNEF-2A",
    },
    12: {
        "06": {"a_hex_in": 0.875, "b_in": 0.97, "c_in": 0.88},
        "16": {"a_hex_in": 0.938, "b_in": 1.03, "c_in": 0.94},
        "d_in": 0.650,
        "e_thread": ".7500-28 UN-2B",
        "f_thread": ".6875-24 UNEF-2A",
    },
}

# Series 800 recommended coupling torque (in-lbs), Glenair torque sheet.
COUPLING_TORQUE_IN_LBS = {
    5: (16, 20),
    6: (18, 22),
    7: (20, 24),
    8: (20, 24),
    9: (20, 24),
    10: (20, 24),
    12: (20, 24),
}

CONTACT_SIZES = {
    "23": {
        "awg_min": 22,
        "awg_max": 28,
        "current_rating": 5.0,
        "dwv_vac": 750,
        "crimp_tool": "M22520/2-01",
        "positioner": "Glenair 809-005",
        "insertion_extraction_tool": "Glenair 809-088",
    },
    "20HD": {
        "awg_min": 20,
        "awg_max": 24,
        "current_rating": 7.5,
        "dwv_vac": 1000,
        "crimp_tool": "M22520/2-01",
        "positioner": "Glenair 809-206",
        "insertion_extraction_tool": "Glenair 809-203",
    },
    "16": {
        "awg_min": 16,
        "awg_max": 20,
        "current_rating": 13.0,
        "dwv_vac": 1800,
        "crimp_tool": "M22520/1-01",
        "positioner": "Glenair 809-137",
        "insertion_extraction_tool": "Glenair 809-131",
    },
    "12": {
        "awg_min": 12,
        "awg_max": 16,
        "current_rating": 23.0,
        "dwv_vac": 1800,
        "crimp_tool": "M22520/1-01",
        "positioner": "Glenair 809-137",
        "insertion_extraction_tool": "Glenair 809-132",
    },
}


def _numbered_contacts(count, size):
    return [{"name": str(i), "size": size} for i in range(1, count + 1)]


# Same-size layouts from Glenair Series 800 contact-arrangement sheets D-4/D-5.
# Combo (mixed-size) arrangements are omitted; pin IDs are not tabulated as a
# flat list on those sheets.
INSERT_ARRANGEMENTS = {
    # Size #23, 750 VAC
    "5-3": _numbered_contacts(3, "23"),
    "6-4": _numbered_contacts(4, "23"),
    "6-6": _numbered_contacts(6, "23"),
    "6-7": _numbered_contacts(7, "23"),
    "7-10": _numbered_contacts(10, "23"),
    "8-13": _numbered_contacts(13, "23"),
    "9-19": _numbered_contacts(19, "23"),
    "10-26": _numbered_contacts(26, "23"),
    "12-37": _numbered_contacts(37, "23"),
    # Size #20HD, 1000 VAC
    "6-23": _numbered_contacts(3, "20HD"),
    "7-25": _numbered_contacts(5, "20HD"),
    "8-28": _numbered_contacts(8, "20HD"),
    "9-210": _numbered_contacts(10, "20HD"),
    "12-220": _numbered_contacts(20, "20HD"),
    # Size #16, 1800 VAC
    "6-1": _numbered_contacts(1, "16"),
    "8-2": _numbered_contacts(2, "16"),
    "9-4": _numbered_contacts(4, "16"),
    "10-5": _numbered_contacts(5, "16"),
    "12-7": _numbered_contacts(7, "16"),
    # Size #12, 1800 VAC
    "7-1": _numbered_contacts(1, "12"),
    "10-2": _numbered_contacts(2, "12"),
    "12-2": _numbered_contacts(2, "12"),
    "12-3": _numbered_contacts(3, "12"),
}

CONTACT_TYPES = ["P", "S"]
KEYS = ["N", "X", "Y", "Z"]

# Finish colors approximated from D38999 / M85049 hardware photos:
# https://d38999.federalconnectors.com/
FINISH_DRAWING_COLORS = {
    "C": {  # Black anodize — deep charcoal, non-conductive
        "body": "#2A2A2A",
        "light": "#444444",
        "dark": "#1A1A1A",
        "specular": "#666666",
        "rim": "#111111",
        "knurl": "#555555",
        "metallic": False,
    },
    "M": {  # Electroless nickel — bright chrome-like silver
        "body": "#C5CAD0",
        "light": "#E8ECF0",
        "dark": "#6E757C",
        "specular": "#FBFCFF",
        "rim": "#4A5056",
        "knurl": "#5A6168",
        "metallic": True,
    },
    "NF": {  # Cadmium olive drab
        "body": "#6B6C38",
        "light": "#8E8F52",
        "dark": "#3E3F22",
        "specular": "#B8B86A",
        "rim": "#2C2D18",
        "knurl": "#2E2F16",
        "metallic": False,
    },
    "ZNU": {  # Zinc-nickel black chromate
        "body": "#3D3E40",
        "light": "#5A5B5D",
        "dark": "#1E1F21",
        "specular": "#7A7B7D",
        "rim": "#141516",
        "knurl": "#6A6B6D",
        "metallic": False,
    },
    "MT": {  # Nickel-PTFE — duller grey
        "body": "#9B9E9A",
        "light": "#B8BBB7",
        "dark": "#5E615D",
        "specular": "#D0D3CF",
        "rim": "#454844",
        "knurl": "#4E514D",
        "metallic": False,
    },
    "Z1": {  # Stainless steel, passivated
        "body": "#A3A4A0",
        "light": "#C8C9C5",
        "dark": "#6E6F6C",
        "specular": "#E8E9E6",
        "rim": "#4A4B48",
        "knurl": "#5C5D5A",
        "metallic": True,
    },
}
_DEFAULT_FINISH_COLORS = {
    "body": "#C0C0C0",
    "light": "#D8D8D8",
    "dark": "#A8A8A8",
    "specular": "#F0F0F0",
    "rim": "#444444",
    "knurl": "#555555",
    "metallic": True,
}
STROKE_COLOR = "#222222"
STROKE_WIDTH = 1.5

FLAGNOTE_ANGLES_DEG = list(range(-180, 180, 15))
FLAGNOTE_OFFSET_IN = 2.0
MIN_LEADER_RADIUS_IN = 0.2
MIN_FLAGNOTE_CLEARANCE_IN = 0.5


def px_in(inches):
    return inches * PX_PER_IN


def finish_palette(finish):
    p = FINISH_DRAWING_COLORS.get((finish or "").upper(), _DEFAULT_FINISH_COLORS)
    return {**_DEFAULT_FINISH_COLORS, **p}


def _diamond_pattern(pid, color):
    return (
        f'<pattern id="{pid}" width="8" height="8" patternUnits="userSpaceOnUse">\n'
        f'  <path d="M0,8 L8,0 M-2,2 L2,-2 M6,10 L10,6" '
        f'stroke="{color}" stroke-width="0.85" fill="none"/>\n'
        f'  <path d="M0,0 L8,8 M-2,6 L2,10 M6,-2 L10,2" '
        f'stroke="{color}" stroke-width="0.85" fill="none"/>\n'
        f"</pattern>"
    )


def finish_svg_defs(part_number, finish):
    body = finish_palette(finish)
    # Harnice lowercases fill url() ids when rasterizing; keep pattern ids lowercased.
    slug = part_number.lower()
    return "\n".join(
        [
            "<!-- Finish colors approximated from https://d38999.federalconnectors.com/ -->",
            "<!-- Silhouette from Glenair 800-006 / 800-007 / 800-008 / 800-009 drawing -->",
            "<defs>",
            _diamond_pattern(f"{slug}-knurl-diamond", body["knurl"]),
            _diamond_pattern(f"{slug}-knurl-diamond-nut", body["knurl"]),
            "</defs>",
        ]
    )


def finish_fills(part_number, finish):
    body = finish_palette(finish)
    slug = part_number.lower()
    return {
        "body": body["body"],
        "nut": body["dark"],
        "band": body["body"],
        "diamond": f"url(#{slug}-knurl-diamond)",
        "diamond_nut": f"url(#{slug}-knurl-diamond-nut)",
        "rim": body["rim"],
    }


def _stroke_attr(stroke, stroke_width):
    if stroke is None:
        return ' stroke="none"'
    return f' stroke="{stroke}" stroke-width="{stroke_width}"'


def _rect(x, y, w, h, fill="#C0C0C0", stroke=STROKE_COLOR, stroke_width=STROKE_WIDTH, extra=""):
    extra_attr = f" {extra}" if extra else ""
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
        f'fill="{fill}"{_stroke_attr(stroke, stroke_width)}{extra_attr}/>'
    )


def _poly(points, fill="#C0C0C0", stroke=STROKE_COLOR, stroke_width=STROKE_WIDTH, extra=""):
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    extra_attr = f" {extra}" if extra else ""
    return (
        f'<polygon points="{pts}" fill="{fill}"'
        f'{_stroke_attr(stroke, stroke_width)}{extra_attr}/>'
    )


def style_dims(shell_size, shell_style):
    data = SHELL_DATA[shell_size]
    return data[shell_style], data["d_in"]


def part_perimeter_inches(shell_size, shell_style):
    """Outer silhouette vertices in inches (math coords, +Y up), CCW, closed.

    Origin at the right end of the banding knurl; knurl/cable −X; body +X to
    the connector face.
    """
    style, d_in = style_dims(shell_size, shell_style)
    half_b = style["b_in"] / 2
    half_c = style["c_in"] / 2
    half_d = d_in / 2
    body = BODY_IN
    band = BAND_PLATFORM_IN
    nut = body * 0.38
    taper = body * 0.12

    x0 = -band
    x1 = 0.0
    x2 = taper
    x3 = body - nut
    x4 = body
    pts = [
        (x0, half_d),
        (x1, half_d),
        (x2, half_c),
        (x3, half_c),
        (x3, half_b),
        (x4, half_b),
        (x4, -half_b),
        (x3, -half_b),
        (x3, -half_c),
        (x2, -half_c),
        (x1, -half_d),
        (x0, -half_d),
    ]
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    return pts


def plug_svg(part_number, shell_size, shell_style, finish=None):
    """Knurl in −X under the cable; origin at right end of knurl; body +X to face."""
    style, d_in = style_dims(shell_size, shell_style)
    fills = finish_fills(part_number, finish)

    b = px_in(style["b_in"])
    c = px_in(style["c_in"])
    d = px_in(d_in)
    body_len = px_in(BODY_IN)
    band_len = px_in(BAND_PLATFORM_IN)
    nut_len = body_len * 0.38
    taper_len = body_len * 0.12

    half_b = b / 2
    half_c = c / 2
    half_d = d / 2

    x0 = -band_len
    x1 = 0.0
    x2 = taper_len
    x3 = body_len - nut_len
    x4 = body_len

    outline = [
        (x0, -half_d),
        (x1, -half_d),
        (x2, -half_c),
        (x3, -half_c),
        (x3, -half_b),
        (x4, -half_b),
        (x4, half_b),
        (x3, half_b),
        (x3, half_c),
        (x2, half_c),
        (x1, half_d),
        (x0, half_d),
    ]

    lip = max(3.0, band_len * 0.12)
    knurl_w = band_len - lip
    nut_knurl_w = nut_len * 0.70

    parts = [
        finish_svg_defs(part_number, finish),
        _poly(outline, fill=fills["body"]),
        _rect(x3, -half_b, nut_len, b, fill=fills["nut"], stroke=None),
        _rect(
            x3,
            -half_b,
            nut_knurl_w,
            b,
            fill=fills["diamond_nut"],
            stroke=None,
            extra='opacity="0.55"',
        ),
        _rect(
            x0 + lip,
            -half_d,
            knurl_w,
            d,
            fill=fills["diamond"],
            stroke=None,
            extra='opacity="0.55"',
        ),
        _poly(outline, fill="none"),
    ]

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="400" height="400">
<g id="{part_number}-drawing-contents-start">
{chr(10).join(p for p in parts if p)}
</g>
<g id="{part_number}-drawing-contents-end">
</g>
</svg>'''


def connector_csys():
    """Connector mating face csys in inches (cartesian; omit polar keys).

    Harnice treats cartesian (x/y) and polar (angle/distance) as exclusive:
    if x/y are present, even as 0.0, polar is ignored.
    """
    return {"x": round(BODY_IN, 4), "y": 0, "rotation": 0}


INCH_TO_MM = 25.4
MM_PER_IN = INCH_TO_MM

# Pin STEP only: shallow scoop-proof cup (~Series 800 mating engagement).
# Part origin is the cable-side knurl (same as the drawing); the cup stays
# at the mating face. No keying / annulus (Mighty Mouse plugs here have no
# backshell interface).
PIN_CAVITY_DEPTH_MM = 0.3 * MM_PER_IN
PIN_CAVITY_WALL_MM = (19.0 - 15.75) / 2.0


def envelope_stations(shell_size, shell_style):
    """Stepped cylinder stations (x_mm, radius_mm) matching the 2D silhouette."""
    style, d_in = style_dims(shell_size, shell_style)
    half_b = style["b_in"] * INCH_TO_MM / 2.0
    half_c = style["c_in"] * INCH_TO_MM / 2.0
    half_d = d_in * INCH_TO_MM / 2.0
    body = BODY_IN * INCH_TO_MM
    band = BAND_PLATFORM_IN * INCH_TO_MM
    nut = body * 0.38
    taper = body * 0.12
    return [
        (-band, half_d),
        (0.0, half_d),
        (taper, half_c),
        (body - nut, half_c),
        (body - nut, half_b),
        (body, half_b),
    ]


def pin_mating_cavity(stations):
    """Scoop-proof cup from the mating face (pin STEP), or None."""
    _x_face, r_face = stations[-1]
    radius = r_face - PIN_CAVITY_WALL_MM
    if radius <= 0.2:
        return None
    return {"dia_mm": 2.0 * radius, "depth_mm": PIN_CAVITY_DEPTH_MM}


def step_origin_x_mm(stations, contact_type):
    """X of the STEP origin in envelope coordinates.

    Cable-side / drawing origin (x = 0). The knurl and cable overlap −X;
    +X is toward the mating face. Pin cups stay at the mating face — they
    do not move the part origin.
    """
    del stations, contact_type
    return 0.0


def shift_stations(stations, origin_x):
    return [(x - origin_x, radius) for x, radius in stations]


def csys_6dof_mm(x_mm, y_mm, z_mm, rx=0.0, ry=0.0, rz=0.0):
    """Child csys pose in inches/degrees relative to the STEP (part) origin.

    (x, y, z) locates the child origin. (rx, ry, rz) are intrinsic XYZ Euler
    rotations of the child axes, so the pose fully constrains 6 DOF.
    """
    return {
        "x": round(float(x_mm) / MM_PER_IN, 4),
        "y": round(float(y_mm) / MM_PER_IN, 4),
        "z": round(float(z_mm) / MM_PER_IN, 4),
        "rx": round(float(rx), 4),
        "ry": round(float(ry), 4),
        "rz": round(float(rz), 4),
    }


def mate_csys_3d(shell_size, shell_style, contact_type):
    """Mating face in the STEP frame (inches), identity orientation.

    Origin is the cable-side knurl; this output sits on the mating face.
    """
    stations = envelope_stations(shell_size, shell_style)
    origin_x = step_origin_x_mm(stations, contact_type)
    return csys_6dof_mm(stations[-1][0] - origin_x, 0.0, 0.0)


def pin_mating_cavity_stations(stations):
    """Fallback profile if OpenCascade is unavailable."""
    cavity = pin_mating_cavity(stations)
    if cavity is None:
        return list(stations)
    x_face = stations[-1][0]
    radius = cavity["dia_mm"] / 2.0
    depth = cavity["depth_mm"]
    return list(stations) + [
        (x_face, radius),
        (x_face - depth, radius),
    ]


def _ocp_positive_solid(stations):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    body = step_utils._ocp_revolution_solid(stations)
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(body, props)
    if props.Mass() < 0:
        body.Reverse()
    return body


def _ocp_cut(body, tool, label):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut

    op = BRepAlgoAPI_Cut(body, tool)
    op.SetFuzzyValue(0.05)
    op.Build()
    cut = op.Shape()
    if not op.IsDone() or cut.IsNull():
        raise RuntimeError(f"{label} cut failed")
    return cut


def _apply_pin_cavity(body, stations, part_number):
    """Boolean scoop-proof cup at the mating face (pin only)."""
    cavity = pin_mating_cavity(stations)
    if cavity is None:
        return body
    x_face = float(stations[-1][0])
    depth = float(cavity["depth_mm"])
    tool = step_utils._ocp_cylinder(
        (x_face - depth, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        float(cavity["dia_mm"]) / 2.0,
        depth + 1.0,
    )
    return _ocp_cut(body, tool, f"{part_number} cavity")


def _write_mating_step(path, part_number, stations, contact_type):
    """Solid envelope; pin STEPs get a shallow mating-face cup."""
    body = _ocp_positive_solid(stations)
    if str(contact_type).upper() == "P":
        body = _apply_pin_cavity(body, stations, part_number)
    step_utils._ocp_write_shape(body, path, part_number)
    return path


def write_part_step(rev_dir, part_number, shell_size, shell_style, contact_type="S"):
    """Write STEP envelope at the cable-side origin; pins include a mating-face cup."""
    path = os.path.join(rev_dir, f"{part_number}-rev{REVISION}-model.step")
    gender = "pin" if str(contact_type).upper() == "P" else "socket"
    description = (
        f"Glenair Series 800 Mighty Mouse low-fidelity envelope ({gender} mating face)"
    )
    stations = envelope_stations(shell_size, shell_style)
    origin_x = step_origin_x_mm(stations, contact_type)
    stations = shift_stations(stations, origin_x)
    try:
        return _write_mating_step(path, part_number, stations, contact_type)
    except ImportError:
        if str(contact_type).upper() == "P":
            step_utils.write_revolution_step(
                path,
                part_number,
                pin_mating_cavity_stations(stations),
                description=description,
            )
        else:
            step_utils.write_revolution_step(
                path, part_number, stations, description=description
            )
        return path


def connector_mating_face_inches(shell_size, shell_style):
    half_b = style_dims(shell_size, shell_style)[0]["b_in"] / 2
    return (BODY_IN, half_b), (BODY_IN, -half_b)


def cable_entry_face_inches(shell_size, shell_style):
    half_d = style_dims(shell_size, shell_style)[1] / 2
    x = -BAND_PLATFORM_IN
    return (x, half_d), (x, -half_d)


def _polygon_centroid(pts):
    verts = pts[:-1] if pts and pts[0] == pts[-1] else pts
    n = len(verts)
    if n < 3:
        if not verts:
            return 0.0, 0.0
        return (
            sum(v[0] for v in verts) / n,
            sum(v[1] for v in verts) / n,
        )

    area2 = 0.0
    cx = cy = 0.0
    for i in range(n):
        x0, y0 = verts[i]
        x1, y1 = verts[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross

    if abs(area2) < 1e-12:
        return (
            sum(v[0] for v in verts) / n,
            sum(v[1] for v in verts) / n,
        )
    inv = 1.0 / (3.0 * area2)
    return cx * inv, cy * inv


def _point_segment_distance(px, py, a, b):
    ax, ay = a
    bx, by = b
    ex, ey = bx - ax, by - ay
    L2 = ex * ex + ey * ey
    if L2 < 1e-18:
        return math.hypot(px - ax, py - ay)
    u = max(0.0, min(1.0, ((px - ax) * ex + (py - ay) * ey) / L2))
    return math.hypot(px - (ax + u * ex), py - (ay + u * ey))


def _point_perimeter_distance(px, py, perimeter):
    if perimeter[0] != perimeter[-1]:
        perimeter = perimeter + [perimeter[0]]
    return min(
        _point_segment_distance(px, py, perimeter[i], perimeter[i + 1])
        for i in range(len(perimeter) - 1)
    )


def _points_close(a, b, tol=1e-4):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def _same_segment(a0, a1, b0, b1, tol=1e-4):
    return (_points_close(a0, b0, tol) and _points_close(a1, b1, tol)) or (
        _points_close(a0, b1, tol) and _points_close(a1, b0, tol)
    )


def _ray_edge_intersection_t(origin, angle_rad, p0, p1, eps=1e-9):
    ox, oy = origin
    dx, dy = math.cos(angle_rad), math.sin(angle_rad)
    ex, ey = p1[0] - p0[0], p1[1] - p0[1]
    det = dx * ey - dy * ex
    if abs(det) < eps:
        return None
    rx, ry = p0[0] - ox, p0[1] - oy
    t = (rx * ey - ry * ex) / det
    u = (rx * dy - ry * dx) / det
    if t < -eps or u < -eps or u > 1 + eps:
        return None
    return max(0.0, t)


def _ray_perimeter_exit_distance(origin, angle_deg, perimeter, exclude_edges=None):
    if perimeter[0] != perimeter[-1]:
        perimeter = perimeter + [perimeter[0]]
    exclude_edges = exclude_edges or []
    angle_rad = math.radians(angle_deg)
    hits = []
    for i in range(len(perimeter) - 1):
        p0, p1 = perimeter[i], perimeter[i + 1]
        if any(_same_segment(p0, p1, e0, e1) for e0, e1 in exclude_edges):
            continue
        t = _ray_edge_intersection_t(origin, angle_rad, p0, p1)
        if t is not None and t > 1e-6:
            hits.append(t)
    if not hits:
        return None
    return max(hits)


def _angle_diff_deg(a, b):
    d = (a - b + 180.0) % 360.0 - 180.0
    if d <= -180.0:
        d += 360.0
    return d


def _order_angles_from_bisector(angles, bisector):
    if not angles:
        return []
    first = min(angles, key=lambda a: abs(_angle_diff_deg(a, bisector)))
    first_diff = _angle_diff_deg(first, bisector)
    left = sorted(
        (a for a in angles if _angle_diff_deg(a, bisector) < first_diff - 1e-9),
        key=lambda a: -_angle_diff_deg(a, bisector),
    )
    right = sorted(
        (a for a in angles if _angle_diff_deg(a, bisector) > first_diff + 1e-9),
        key=lambda a: _angle_diff_deg(a, bisector),
    )
    ordered = [first]
    for i in range(max(len(left), len(right))):
        if i < len(left):
            ordered.append(left[i])
        if i < len(right):
            ordered.append(right[i])
    return ordered


def flagnote_csys_children(shell_size, shell_style):
    """Flagnotes about the silhouette centroid (straight plug).

    Stored as absolute x/y (harnice treats x/y vs angle/distance as exclusive).
    """
    perimeter = part_perimeter_inches(shell_size, shell_style)
    cx, cy = _polygon_centroid(perimeter)
    origin = (cx, cy)
    bisector = 90.0

    exclude = [
        connector_mating_face_inches(shell_size, shell_style),
        cable_entry_face_inches(shell_size, shell_style),
    ]

    leaders = []
    for angle in FLAGNOTE_ANGLES_DEG:
        r_leader = _ray_perimeter_exit_distance(
            origin, angle, perimeter, exclude_edges=exclude
        )
        if r_leader is None or r_leader < MIN_LEADER_RADIUS_IN:
            continue
        leaders.append((angle, r_leader))

    if not leaders:
        return {
            "leader_center": {
                "x": round(cx, 4),
                "y": round(cy, 4),
                "rotation": 0,
            }
        }

    r_flag = max(r for _, r in leaders) + FLAGNOTE_OFFSET_IN

    kept = []
    for angle, r_leader in leaders:
        rad = math.radians(angle)
        fx = cx + r_flag * math.cos(rad)
        fy = cy + r_flag * math.sin(rad)
        if _point_perimeter_distance(fx, fy, perimeter) < MIN_FLAGNOTE_CLEARANCE_IN:
            continue
        kept.append((angle, r_leader))

    by_angle = {angle: r for angle, r in kept}
    ordered_angles = _order_angles_from_bisector(list(by_angle), bisector)
    kept = [(angle, by_angle[angle]) for angle in ordered_angles]

    children = {
        "leader_center": {
            "x": round(cx, 4),
            "y": round(cy, 4),
            "rotation": 0,
        }
    }
    for i, (angle, r_leader) in enumerate(kept, start=1):
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        children[f"flagnote-{i}-leader_dest"] = {
            "x": round(cx + r_leader * cos_a, 4),
            "y": round(cy + r_leader * sin_a, 4),
            "rotation": 0,
        }
        children[f"flagnote-{i}"] = {
            "x": round(cx + r_flag * cos_a, 4),
            "y": round(cy + r_flag * sin_a, 4),
            "rotation": 0,
        }
    return children



# Glenair Series 800 cable-plug maximum weight, grams.
# https://www.glenair.com/mighty-mouse/series-800-un-thread-mating/pdf/connector-weights.pdf
# Table is aluminum. Style 16 (wave-spring nut) is ~12% heavier from the
# larger hex. Stainless (Z1) uses density ratio 8.0/2.70.
MASS_SOURCE = (
    "Glenair Series 800 cable-plug maximum weights, grams: "
    "https://www.glenair.com/mighty-mouse/series-800-un-thread-mating/pdf/connector-weights.pdf "
    "Table is aluminum. Style 16 is scaled +12% for the larger hex nut; "
    "stainless Z1 is scaled by density ratio 8.0/2.70."
)
MASS_PLUG_G = {
    "5-3": {"P": 3.6, "S": 3.7},
    "6-1": {"P": 4.3, "S": 4.4},
    "6-4": {"P": 4.8, "S": 5.2},
    "6-6": {"P": 4.9, "S": 5.3},
    "6-7": {"P": 4.8, "S": 4.7},
    "6-23": {"P": 4.3, "S": 4.6},
    "7-1": {"P": 5.7, "S": 5.9},
    "7-10": {"P": 6.9, "S": 7.4},
    "7-25": {"P": 5.6, "S": 5.9},
    "8-2": {"P": 7.4, "S": 8.1},
    "8-13": {"P": 6.7, "S": 7.2},
    "8-28": {"P": 7.6, "S": 8.6},
    "9-4": {"P": 8.7, "S": 8.8},
    "9-19": {"P": 10.5, "S": 11.2},
    "9-210": {"P": 8.5, "S": 8.8},
    "10-2": {"P": 9.5, "S": 10.8},
    "10-5": {"P": 9.7, "S": 11.1},
    "10-26": {"P": 7.9, "S": 8.6},
    "12-2": {"P": 10.5, "S": 10.6},
    "12-3": {"P": 10.7, "S": 10.8},
    "12-7": {"P": 14.3, "S": 16.9},
    "12-37": {"P": 12.5, "S": 16.1},
    "12-220": {"P": 11.3, "S": 12.2},
}


def part_mass_lbs(shell_style, finish, insert_arrangement, contact_type):
    grams = MASS_PLUG_G[insert_arrangement][contact_type]
    if str(shell_style) == "16":
        grams *= 1.12
    if finish == "Z1":
        grams *= 8.0 / 2.70
    return grams / 453.59237


def compile_part_attributes(part_configuration):
    shell_size = part_configuration["shell_size"]
    shell_style = part_configuration["shell_style"]
    insert_arrangement = part_configuration["insert_arrangement"]
    contacts = INSERT_ARRANGEMENTS[insert_arrangement]

    seen_contact_sizes = []
    for contact in contacts:
        if contact["size"] not in seen_contact_sizes:
            seen_contact_sizes.append(contact["size"])

    tools = []
    for contact_size in seen_contact_sizes:
        spec = CONTACT_SIZES[contact_size]
        tools.append(f"{spec['crimp_tool']} crimp tool")
        tools.append(f"{spec['positioner']} positioner")
        tools.append(f"{spec['insertion_extraction_tool']} insertion/extraction tool")
    tools.append("Glenair 601-101 Band-Master ATS micro banding tool")

    tmin, tmax = COUPLING_TORQUE_IN_LBS[shell_size]
    csys = {
        "3d-mate": mate_csys_3d(
            shell_size, shell_style, part_configuration["contact_type"]
        ),
        "connector": connector_csys(),
    }
    csys.update(flagnote_csys_children(shell_size, shell_style))

    return {
        "mass": f"{part_mass_lbs(shell_style, part_configuration['finish'], insert_arrangement, part_configuration['contact_type']):.4f}lbs",
        "mass_source": MASS_SOURCE,
        "tools": tools,
        "build_notes": [
            f"Torque coupling nut to {tmin}-{tmax} in-lbs during harness installation",
        ],
        "csys_children": csys,
        "contacts": contacts,
        "shell_size": shell_size,
    }


def make_part_number(shell_style, finish, insert_arrangement, contact_type, key):
    # Glenair sample: 800-006-06M6-7PN
    return f"800-006-{shell_style}{finish}{insert_arrangement}{contact_type}{key}"


def iter_part_configurations():
    for shell_style in SHELL_STYLES:
        for finish in FINISHES:
            for insert_arrangement in INSERT_ARRANGEMENTS:
                shell_size = int(insert_arrangement.split("-")[0])
                for contact_type in CONTACT_TYPES:
                    for key in KEYS:
                        yield {
                            "shell_style": shell_style,
                            "finish": finish,
                            "shell_size": shell_size,
                            "insert_arrangement": insert_arrangement,
                            "contact_type": contact_type,
                            "key": key,
                        }


def _progress_bar(done, total, width=25):
    if total <= 0:
        filled = width
        pct = 100
    else:
        filled = min(width, max(0, round(width * done / total)))
        pct = round(100.0 * done / total)
    cells = ["x"] * filled + ["."] * (width - filled)
    return "[ " + " ".join(cells) + f" ] ({pct}%)"


def main(step_only=False, dry_run=False):
    state.set_rev(REVISION)
    state.set_project_type("part")

    configs = list(iter_part_configurations())
    total = len(configs)

    if dry_run:
        print(f"{total} legal Mighty Mouse configurations in the permutation space.")
        return

    for i, part_configuration in enumerate(configs, start=1):
        part_number = make_part_number(
            part_configuration["shell_style"],
            part_configuration["finish"],
            part_configuration["insert_arrangement"],
            part_configuration["contact_type"],
            part_configuration["key"],
        )
        print(part_number, flush=True)

        family_dir = os.path.dirname(os.path.abspath(__file__))
        part_dir = os.path.join(family_dir, part_number)
        rev_dir = os.path.join(part_dir, f"{part_number}-rev{REVISION}")

        if step_only:
            os.makedirs(rev_dir, exist_ok=True)
            json_path = os.path.join(
                rev_dir, f"{part_number}-rev{REVISION}-attributes.json"
            )
            with open(json_path, "w") as f:
                json.dump(compile_part_attributes(part_configuration), f, indent=2)
            write_part_step(
                rev_dir,
                part_number,
                part_configuration["shell_size"],
                part_configuration["shell_style"],
                part_configuration["contact_type"],
            )
            print(_progress_bar(i, total), flush=True)
            continue

        os.makedirs(part_dir, exist_ok=True)

        revision_history_content_dict = {
            "project_type": state.project_type,
            "mfg": "Glenair",
            "pn": part_number,
            "rev": REVISION,
            "desc": "",
            "status": "",
            "datestarted": DATE_STARTED,
            "library_repo": "https://github.com/harnice/harnice-aerospace-library",
            "library_subpath": "mighty_mouse",
        }
        revision_history_csv_path = os.path.join(
            part_dir, f"{part_number}-revision_history.tsv"
        )
        rev_history.part_family_append(
            revision_history_content_dict, revision_history_csv_path
        )

        rev_dir = os.path.join(part_dir, f"{part_number}-rev{REVISION}")
        if os.path.exists(rev_dir):
            for item in os.listdir(rev_dir):
                item_path = os.path.join(rev_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
        else:
            os.makedirs(rev_dir)

        json_path = os.path.join(
            rev_dir, f"{part_number}-rev{REVISION}-attributes.json"
        )
        attributes = compile_part_attributes(part_configuration)
        with open(json_path, "w") as f:
            json.dump(attributes, f, indent=2)

        svg_content = plug_svg(
            part_number,
            part_configuration["shell_size"],
            part_configuration["shell_style"],
            part_configuration["finish"],
        )
        svg_path = os.path.join(rev_dir, f"{part_number}-rev{REVISION}-drawing.svg")
        with open(svg_path, "w") as f:
            f.write(svg_content)

        write_part_step(
            rev_dir,
            part_number,
            part_configuration["shell_size"],
            part_configuration["shell_style"],
            part_configuration["contact_type"],
        )

        subprocess.run(
            ["harnice", "-b"],
            cwd=rev_dir,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if delete_pngs:
            for item in os.listdir(rev_dir):
                if item.endswith(".png"):
                    os.remove(os.path.join(rev_dir, item))

        print(_progress_bar(i, total), flush=True)

    print("Finished rendering all parts in family.")


if __name__ == "__main__":
    main()
