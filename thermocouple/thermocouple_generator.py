"""
thermocouple_generator.py
=========================

Standard-size round-pin thermocouple connectors (ASTM E1129 / Omega OST).

PRIMARY SOURCES
---------------
    ASTM E1129/E1129M, "Standard Specification for Thermocouple Connectors."
    Table 1 mating dimensions (prong diameters, spacing, length, body maxima);
    Table 2 ANSI/ASTM body colors. Round pins; negative pin is larger.

    Omega OSTW / HSTW catalog drawing (Most Popular Standard Connectors,
    page G-11). Typical glass-filled nylon body used for the envelope,
    which sits inside the ASTM maxima:
        https://assets.omega.com/pdf/connectors/thermocouple-and-rtd-connectors/OSTW_HST_OSTW.pdf

    Omega OST how-to-order (legacy no-window standard-size connector,
    plug-compatible with OSTW and other ASTM E1129 round-pin parts):
        https://www.dwyeromega.com/en-us/standard-size-thermocouple-connectors-without-write-on-tag/p/OST

WHAT IS MODELLED
----------------
    One ASTM E1129 envelope shared by every calibration. Male and female
    bodies are the same size; the male adds two round prongs. Color is
    ANSI (MC96.1 / ASTM E1129 Table 2), plus the usual tungsten-rhenium
    markings for C / D / G that Omega and other makers print on the
    same shell.

    Library PN follows Omega OST-{{type}}-{{M|F}}. Type R/S is OST-RS-*
    on disk (Omega catalog PIN is OST-R/S-*).

LIMITATIONS
-----------
    Low-fidelity envelope: rectangular body plus cylindrical prongs on
    the plug. Cover-screw, write-on window, and internal wire divider
    are not solids. Body length/width/thickness are Omega's published
    typical values, not the ASTM maxima.
"""

import csv
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
DATE_STARTED = "8/18/26"
delete_pngs = True

PX_PER_IN = 96.0
MM_PER_IN = 25.4

# ---------------------------------------------------------------------------
# Envelope — Omega OSTW G-11 typical values, checked against ASTM E1129 T1.
# Body L/W/T are typical (ASTM publishes maxima only). Prong geometry is
# the ASTM mid-range / Omega callout.
# ---------------------------------------------------------------------------
BODY_LENGTH_MM = 33.33          # Omega 1.31 in; ASTM L max 38.23 mm
BODY_WIDTH_MM = 25.4            # Omega 1.00 in; ASTM W max 27.64 mm
BODY_THICKNESS_MM = 12.7        # Omega 0.50 in; ASTM T max 13.08 mm
PRONG_LENGTH_MM = 15.06         # Omega 0.59 in; ASTM P 13.59–16.51 mm
PRONG_SPACING_MM = 11.11        # Omega 0.44 in; ASTM X 10.97–11.23 mm
POSITIVE_PIN_DIA_MM = 3.96      # Omega / ASTM D1 mid (3.86–4.02 mm)
NEGATIVE_PIN_DIA_MM = 4.77      # Omega 0.19 in; ASTM D2 4.62–4.83 mm
WIRE_HOLE_DIA_MM = 5.5          # Omega 0.22 in
CAP_LENGTH_MM = 8.0             # Omega rear-section callout 0.31 in
BODY_CORNER_MM = 1.5
MAX_WIRE_AWG = 14
MIN_WIRE_AWG = 30
TEMP_C = (-29, 180)             # glass-filled nylon OST / OSTW
PIN_HEX = "#C0C0C0"             # contact metal in STEP / SVG

# ANSI body colors for the 2D drawing. C/D/G are the usual tungsten-rhenium
# markings on an ASTM-size shell (red; D white insert, G green insert).
TYPES = {
    "RS": {
        "official_code": "R/S",
        "name": "Type R/S",
        "ansi_color": "green",
        "body_hex": "#1B5E3B",
        "cap_hex": None,
        "positive_alloy": "copper (compensating)",
        "negative_alloy": "copper-nickel compensating (RNX/SNX)",
        "used_with": "Type R (Pt13%Rh-Pt) and Type S (Pt10%Rh-Pt)",
    },
    "T": {
        "official_code": "T",
        "name": "Type T",
        "ansi_color": "blue",
        "body_hex": "#1565C0",
        "cap_hex": None,
        "positive_alloy": "copper",
        "negative_alloy": "constantan",
        "used_with": "Type T (Cu-CuNi)",
    },
    "K": {
        "official_code": "K",
        "name": "Type K",
        "ansi_color": "yellow",
        "body_hex": "#F2C200",
        "cap_hex": None,
        "positive_alloy": "chromel (Ni-Cr)",
        "negative_alloy": "alumel (Ni-Al)",
        "used_with": "Type K (NiCr-NiAl)",
    },
    "J": {
        "official_code": "J",
        "name": "Type J",
        "ansi_color": "black",
        "body_hex": "#1C1C1C",
        "cap_hex": None,
        "positive_alloy": "iron",
        "negative_alloy": "constantan",
        "used_with": "Type J (Fe-CuNi)",
    },
    "D": {
        "official_code": "D",
        "name": "Type D",
        "ansi_color": "red with white insert",
        "body_hex": "#C62828",
        "cap_hex": "#EDEDED",
        "positive_alloy": "W3%Re compensating",
        "negative_alloy": "W25%Re compensating",
        "used_with": "Type D (W3%Re-W25%Re)",
    },
    "C": {
        "official_code": "C",
        "name": "Type C",
        "ansi_color": "red",
        "body_hex": "#C62828",
        "cap_hex": None,
        "positive_alloy": "W5%Re compensating (CPX)",
        "negative_alloy": "W26%Re compensating (CNX)",
        "used_with": "Type C (W5%Re-W26%Re)",
    },
    "N": {
        "official_code": "N",
        "name": "Type N",
        "ansi_color": "orange",
        "body_hex": "#E65100",
        "cap_hex": None,
        "positive_alloy": "nicrosil",
        "negative_alloy": "nisil",
        "used_with": "Type N (NiCrSi-NiSi)",
    },
    "E": {
        "official_code": "E",
        "name": "Type E",
        "ansi_color": "purple",
        "body_hex": "#7B1FA2",
        "cap_hex": None,
        "positive_alloy": "chromel (Ni-Cr)",
        "negative_alloy": "constantan",
        "used_with": "Type E (NiCr-CuNi)",
    },
    "G": {
        "official_code": "G",
        "name": "Type G",
        "ansi_color": "red with green insert",
        "body_hex": "#C62828",
        "cap_hex": "#1B5E3B",
        "positive_alloy": "tungsten compensating",
        "negative_alloy": "W26%Re compensating",
        "used_with": "Type G (W-W26%Re)",
    },
    "U": {
        "official_code": "U",
        "name": "Type U (uncompensated)",
        "ansi_color": "white",
        "body_hex": "#F5F5F5",
        "cap_hex": None,
        "positive_alloy": "copper",
        "negative_alloy": "copper",
        "used_with": "Type B (Pt30%Rh-Pt6%Rh); uncompensated Cu/Cu",
    },
}

GENDERS = {
    "M": {
        "name": "Plug",
        "contacts": "pin",
        "omega_suffix": "M",
    },
    "F": {
        "name": "Jack",
        "contacts": "socket",
        "omega_suffix": "F",
    },
}

FLAGNOTE_CENTER_X_IN = 0.0
FLAGNOTE_CENTER_Y_IN = 0.0
FLAGNOTE_RADIUS_IN = 3.0
FLAGNOTE_ANGLES_DEG = (
    0, 15, -15, 30, -30, 45, -45, 60, -60, 75, -75, 90, -90
)


def make_part_number(part_configuration):
    return f"OST-{part_configuration['tc_type']}-{part_configuration['gender']}"


def official_pin(part_configuration):
    code = TYPES[part_configuration["tc_type"]]["official_code"]
    return f"OST-{code}-{part_configuration['gender']}"


def connector_length_mm(gender):
    if gender == "M":
        return BODY_LENGTH_MM + PRONG_LENGTH_MM
    return BODY_LENGTH_MM


def _flagnote_note_polar(theta_deg):
    rad = math.radians(theta_deg)
    nx = FLAGNOTE_CENTER_X_IN + FLAGNOTE_RADIUS_IN * math.cos(rad)
    ny = FLAGNOTE_CENTER_Y_IN + FLAGNOTE_RADIUS_IN * math.sin(rad)
    if nx < 0.0:
        nx = 0.0
        radial = math.sqrt(
            max(
                FLAGNOTE_RADIUS_IN ** 2
                - (nx - FLAGNOTE_CENTER_X_IN) ** 2,
                0.0,
            )
        )
        ny = math.copysign(radial, math.sin(rad) or theta_deg)
    return (
        math.degrees(math.atan2(ny - FLAGNOTE_CENTER_Y_IN, nx - FLAGNOTE_CENTER_X_IN)),
        math.hypot(nx - FLAGNOTE_CENTER_X_IN, ny - FLAGNOTE_CENTER_Y_IN),
    )


def _even_face_ys(half_h, count):
    if count <= 1:
        return [0.0]
    step = (2.0 * half_h) / (count - 1)
    ys = [0.0]
    for j in range(1, (count + 1) // 2):
        ys.append(j * step)
        ys.append(-j * step)
    if len(ys) < count:
        ys.append((count // 2) * step)
    return ys


def flagnote_csys_children(mating_face_x_in, mating_face_half_height_mm):
    """Polar flagnotes from the origin; leaders spaced along the mating face.

    Harnice treats cartesian (x/y) and polar (angle/distance) as exclusive:
    if x/y are present, even as 0.0, polar is ignored. Emit polar only.
    """
    half_h_in = mating_face_half_height_mm / MM_PER_IN
    dx = mating_face_x_in - FLAGNOTE_CENTER_X_IN
    kept = []
    for theta in FLAGNOTE_ANGLES_DEG:
        note_angle, note_dist = _flagnote_note_polar(theta)
        note_x = FLAGNOTE_CENTER_X_IN + note_dist * math.cos(math.radians(note_angle))
        if note_x < mating_face_x_in:
            continue
        kept.append((note_angle, note_dist))
    children = {}
    for i, ((note_angle, note_dist), y_face) in enumerate(
        zip(kept, _even_face_ys(half_h_in, len(kept))), start=1
    ):
        theta_dest = math.degrees(
            math.atan2(y_face - FLAGNOTE_CENTER_Y_IN, dx)
        )
        dist_face = math.hypot(dx, y_face - FLAGNOTE_CENTER_Y_IN)
        children[f"flagnote-{i}-leader_dest"] = {
            "angle": theta_dest,
            "distance": dist_face,
            "rotation": 0,
        }
        children[f"flagnote-{i}"] = {
            "angle": note_angle,
            "distance": note_dist,
            "rotation": 0,
        }
    return children


def _px_mm(mm):
    return (mm / MM_PER_IN) * PX_PER_IN


def _poly(points, fill="#C0C0C0"):
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}" stroke="black" stroke-width="1"/>'


def _arc_yz(cy, cz, radius, a0, a1, n):
    pts = []
    for i in range(n + 1):
        t = a0 + (a1 - a0) * i / n
        pts.append((cy + radius * math.cos(t), cz + radius * math.sin(t)))
    return pts


def _rounded_rect_yz(width_mm, height_mm, radius_mm=BODY_CORNER_MM, n=6):
    hw, hh = width_mm / 2.0, height_mm / 2.0
    r = min(radius_mm, hw * 0.45, hh * 0.45)
    if r < 0.05:
        return [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    pts = []
    pts += _arc_yz(hw - r, -hh + r, r, -math.pi / 2, 0.0, n)
    pts += _arc_yz(hw - r, hh - r, r, 0.0, math.pi / 2, n)
    pts += _arc_yz(-hw + r, hh - r, r, math.pi / 2, math.pi, n)
    pts += _arc_yz(-hw + r, -hh + r, r, math.pi, 3.0 * math.pi / 2, n)
    return pts


def _circle_yz(cy, cz, radius_mm, n=12):
    return [
        (
            cy + radius_mm * math.cos(2.0 * math.pi * i / n),
            cz + radius_mm * math.sin(2.0 * math.pi * i / n),
        )
        for i in range(n)
    ]


def envelope_prisms_mm(gender):
    """Low-fi envelope in millimetres.

    Catalog top view is the XY plane, looking toward −Z:
      body length along +X (cable origin → mating face)
      body width (pin row) along ±Y
      body thickness along ±Z
    Male prongs continue +X past the body. Negative prong is larger and
    sits at −Y.
    """
    return [segment for _name, segment, _hex in envelope_colored_parts("K", gender)]


def envelope_colored_parts(tc_type, gender):
    """Named prism segments with ANSI / metal hex colors for STEP styling."""
    spec = TYPES[tc_type]
    body = _rounded_rect_yz(BODY_WIDTH_MM, BODY_THICKNESS_MM)
    parts = []
    if spec["cap_hex"]:
        parts.append(("insert", (0.0, CAP_LENGTH_MM, body), spec["cap_hex"]))
        parts.append(("body", (CAP_LENGTH_MM, BODY_LENGTH_MM, body), spec["body_hex"]))
    else:
        parts.append(("body", (0.0, BODY_LENGTH_MM, body), spec["body_hex"]))
    if gender == "M":
        half = PRONG_SPACING_MM / 2.0
        x0 = BODY_LENGTH_MM
        x1 = x0 + PRONG_LENGTH_MM
        parts.append(
            (
                "positive_pin",
                (x0, x1, _circle_yz(half, 0.0, POSITIVE_PIN_DIA_MM / 2.0)),
                PIN_HEX,
            )
        )
        parts.append(
            (
                "negative_pin",
                (x0, x1, _circle_yz(-half, 0.0, NEGATIVE_PIN_DIA_MM / 2.0)),
                PIN_HEX,
            )
        )
    return parts


def _hex_rgb(hex_color):
    value = hex_color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _write_colored_ost_step(path, part_number, tc_type, gender):
    """AP214 STEP with XCAF surface colors (body / insert / pins)."""
    from OCP.BRep import BRep_Builder
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Interface import Interface_Static
    from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDocStd import TDocStd_Document
    from OCP.TopoDS import TopoDS_Compound
    from OCP.XCAFApp import XCAFApp_Application
    from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool

    Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
    Interface_Static.SetCVal_s("write.step.unit", "MM")

    solids = []
    colors = []
    for name, segment, hex_color in envelope_colored_parts(tc_type, gender):
        solids.append(step_utils._ocp_prism_segments_solid([segment]))
        colors.append((name, _hex_rgb(hex_color)))

    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for solid in solids:
        builder.Add(compound, solid)

    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
    app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    label = shape_tool.AddShape(compound, True)
    TDataStd_Name.Set_s(label, TCollection_ExtendedString(str(part_number)))
    for solid, (_name, rgb) in zip(solids, colors):
        color = Quantity_Color(rgb[0], rgb[1], rgb[2], Quantity_TOC_RGB)
        color_tool.SetColor(solid, color, XCAFDoc_ColorType.XCAFDoc_ColorSurf)
        color_tool.SetColor(solid, color, XCAFDoc_ColorType.XCAFDoc_ColorGen)

    writer = STEPCAFControl_Writer()
    writer.SetNameMode(True)
    writer.SetColorMode(True)
    with step_utils._silence_stdio():
        if not writer.Transfer(doc):
            raise RuntimeError("STEPCAFControl_Writer.Transfer failed")
        status = writer.Write(path)
    try:
        app.Close(doc)
    except Exception:
        pass
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEPCAFControl_Writer.Write failed: {status}")
    return path


def write_part_step(rev_dir, part_number, tc_type, gender):
    path = os.path.join(rev_dir, f"{part_number}-rev{REVISION}-model.step")
    try:
        _write_colored_ost_step(path, part_number, tc_type, gender)
    except ImportError:
        step_utils.write_prism_segments_step(
            path,
            part_number,
            envelope_prisms_mm(gender),
            description="ASTM E1129 / Omega OST low-fidelity envelope",
        )
    return path


def thermocouple_svg(part_number, tc_type, gender):
    """
    Top silhouette: origin at the cable side, +X toward the mating face
    (same convention as D38999 / D-sub). Vertical is body width (pin row).
    Thickness is into the page and not drawn.
    """
    spec = TYPES[tc_type]
    body_px = _px_mm(BODY_LENGTH_MM)
    half_w = _px_mm(BODY_WIDTH_MM) / 2.0
    prong_px = _px_mm(PRONG_LENGTH_MM)
    half_sp = _px_mm(PRONG_SPACING_MM) / 2.0
    pos_r = _px_mm(POSITIVE_PIN_DIA_MM) / 2.0
    neg_r = _px_mm(NEGATIVE_PIN_DIA_MM) / 2.0
    cap_px = _px_mm(CAP_LENGTH_MM) if spec["cap_hex"] else 0.0
    hole_r = _px_mm(WIRE_HOLE_DIA_MM) / 2.0
    screw_r = _px_mm(2.5) / 2.0

    mating_x = body_px + (prong_px if gender == "M" else 0.0)
    outline = [
        (0.0, -half_w),
        (body_px, -half_w),
    ]
    if gender == "M":
        outline.extend(
            [
                (body_px, -half_sp - neg_r),
                (mating_x, -half_sp - neg_r),
                (mating_x, -half_sp + neg_r),
                (body_px, -half_sp + neg_r),
                (body_px, half_sp - pos_r),
                (mating_x, half_sp - pos_r),
                (mating_x, half_sp + pos_r),
                (body_px, half_sp + pos_r),
            ]
        )
    outline.extend(
        [
            (body_px, half_w),
            (0.0, half_w),
        ]
    )

    body_fill = spec["body_hex"]
    parts = [_poly(outline, fill=body_fill)]
    if spec["cap_hex"]:
        parts.append(
            f'<rect x="0.00" y="{-half_w:.2f}" width="{cap_px:.2f}" '
            f'height="{2 * half_w:.2f}" fill="{spec["cap_hex"]}" '
            f'stroke="black" stroke-width="1"/>'
        )
    if gender == "M":
        parts.append(
            f'<rect x="{body_px:.2f}" y="{-half_sp - neg_r:.2f}" '
            f'width="{prong_px:.2f}" height="{2 * neg_r:.2f}" '
            f'fill="{PIN_HEX}" stroke="black" stroke-width="1"/>'
        )
        parts.append(
            f'<rect x="{body_px:.2f}" y="{half_sp - pos_r:.2f}" '
            f'width="{prong_px:.2f}" height="{2 * pos_r:.2f}" '
            f'fill="{PIN_HEX}" stroke="black" stroke-width="1"/>'
        )
    parts.append(
        f'<circle cx="{body_px / 2.0:.2f}" cy="0.00" r="{screw_r:.2f}" '
        f'fill="#6E6E6E" stroke="black" stroke-width="1"/>'
    )
    parts.append(
        f'<circle cx="{_px_mm(2.0):.2f}" cy="{-half_sp:.2f}" r="{hole_r:.2f}" '
        f'fill="none" stroke="black" stroke-width="1"/>'
    )
    parts.append(
        f'<circle cx="{_px_mm(2.0):.2f}" cy="{half_sp:.2f}" r="{hole_r:.2f}" '
        f'fill="none" stroke="black" stroke-width="1"/>'
    )

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="400" height="400">
<g id="{part_number}-drawing-contents-start">
{chr(10).join(parts)}
</g>
<g id="{part_number}-drawing-contents-end">
</g>
</svg>'''



# Omega does not publish a gram weight. ~15.5 g male / ~16.1 g female from
# the OST envelope (glass-filled nylon body plus pins/screws) using dimensions
# from https://assets.omega.com/pdf/connectors/thermocouple-and-rtd-connectors/OSTW_HST_OSTW.pdf
MASS_SOURCE = (
    "Estimated. Omega does not publish a gram weight. ~15.5 g from the OST "
    "envelope (glass-filled nylon body plus pins/screws) using dimensions from "
    "https://assets.omega.com/pdf/connectors/thermocouple-and-rtd-connectors/OSTW_HST_OSTW.pdf"
)


def part_mass_lbs(gender):
    grams = 16.1 if gender == "F" else 15.5
    return grams / 453.59237


def compile_part_attributes(part_configuration):
    gender = part_configuration["gender"]
    length_mm = connector_length_mm(gender)
    return {
        "mass": f"{part_mass_lbs(gender):.4f}lbs",
        "mass_source": MASS_SOURCE,
        "tools": ["Phillips/slot screwdriver"],
        "build_notes": [],
        "csys_children": {
            "3d-mate": {
                "x": round(length_mm / MM_PER_IN, 4),
                "y": 0.0,
                "z": 0.0,
                "rx": 0.0,
                "ry": 0.0,
                "rz": 0.0,
            },
            **flagnote_csys_children(
                length_mm / MM_PER_IN,
                BODY_WIDTH_MM / 2.0,
            ),
        },
        "contacts": [
            {"name": "+", "size": str(MAX_WIRE_AWG)},
            {"name": "-", "size": str(MAX_WIRE_AWG)},
        ],
    }


def iter_part_configurations():
    for tc_type in TYPES:
        for gender in GENDERS:
            yield {"tc_type": tc_type, "gender": gender}


CATALOG_COLUMNS = (
    "library_pn",
    "official_pin",
    "spec",
    "common_name",
    "tc_type",
    "gender",
    "contacts",
    "ansi_color",
    "positive_alloy",
    "negative_alloy",
    "pin_count",
    "max_wire_awg",
    "color_code",
)


def catalog_row(part_configuration):
    spec = TYPES[part_configuration["tc_type"]]
    gender = part_configuration["gender"]
    g = GENDERS[gender]
    return {
        "library_pn": make_part_number(part_configuration),
        "official_pin": official_pin(part_configuration),
        "spec": "ASTM E1129",
        "common_name": f"{spec['name']} standard {g['name'].lower()}",
        "tc_type": spec["official_code"],
        "gender": g["name"],
        "contacts": g["contacts"],
        "ansi_color": spec["ansi_color"],
        "positive_alloy": spec["positive_alloy"],
        "negative_alloy": spec["negative_alloy"],
        "pin_count": 2,
        "max_wire_awg": MAX_WIRE_AWG,
        "color_code": "ANSI",
    }


def write_catalog_csv(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thermocouple.csv")
    rows = [catalog_row(cfg) for cfg in iter_part_configurations()]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _progress_bar(done, total, width=25):
    if total <= 0:
        filled = width
        pct = 100
    else:
        filled = min(width, max(0, round(width * done / total)))
        pct = round(100.0 * done / total)
    cells = ["x"] * filled + ["."] * (width - filled)
    return "[ " + " ".join(cells) + f" ] ({pct}%)"


def make_part(part_configuration):
    part_number = make_part_number(part_configuration)
    print("Preparing part number: ", part_number)

    family_dir = os.path.dirname(os.path.abspath(__file__))
    part_dir = os.path.join(family_dir, part_number)
    os.makedirs(part_dir, exist_ok=True)

    revision_history_content_dict = {
        "project_type": state.project_type,
        "mfg": "Omega",
        "pn": part_number,
        "rev": REVISION,
        "desc": "",
        "status": "",
        "datestarted": DATE_STARTED,
        "library_repo": "https://github.com/harnice/harnice-aerospace-library",
        "library_subpath": "thermocouple",
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

    json_path = os.path.join(rev_dir, f"{part_number}-rev{REVISION}-attributes.json")
    with open(json_path, "w") as f:
        json.dump(compile_part_attributes(part_configuration), f, indent=2)

    svg_path = os.path.join(rev_dir, f"{part_number}-rev{REVISION}-drawing.svg")
    with open(svg_path, "w") as f:
        f.write(
            thermocouple_svg(
                part_number,
                part_configuration["tc_type"],
                part_configuration["gender"],
            )
        )

    write_part_step(
        rev_dir,
        part_number,
        part_configuration["tc_type"],
        part_configuration["gender"],
    )

    subprocess.run(["harnice", "-b"], cwd=rev_dir, check=True)
    if delete_pngs:
        for item in os.listdir(rev_dir):
            if item.endswith(".png"):
                os.remove(os.path.join(rev_dir, item))

    return part_number


def main(step_only=False, csv_only=False, dry_run=False):
    state.set_rev(REVISION)
    state.set_project_type("part")

    if dry_run:
        total = sum(1 for _ in iter_part_configurations())
        print(f"{total} legal thermocouple configurations in the permutation space.")
        return

    csv_path = write_catalog_csv()
    print(f"Wrote catalog: {csv_path}")
    if csv_only:
        return

    configs = list(iter_part_configurations())
    total = len(configs)
    for i, part_configuration in enumerate(configs, start=1):
        if step_only:
            part_number = make_part_number(part_configuration)
            print("Preparing part number: ", part_number)
            family_dir = os.path.dirname(os.path.abspath(__file__))
            rev_dir = os.path.join(
                family_dir, part_number, f"{part_number}-rev{REVISION}"
            )
            os.makedirs(rev_dir, exist_ok=True)
            json_path = os.path.join(
                rev_dir, f"{part_number}-rev{REVISION}-attributes.json"
            )
            with open(json_path, "w") as f:
                json.dump(compile_part_attributes(part_configuration), f, indent=2)
            svg_path = os.path.join(
                rev_dir, f"{part_number}-rev{REVISION}-drawing.svg"
            )
            with open(svg_path, "w") as f:
                f.write(
                    thermocouple_svg(
                        part_number,
                        part_configuration["tc_type"],
                        part_configuration["gender"],
                    )
                )
            write_part_step(
        rev_dir,
        part_number,
        part_configuration["tc_type"],
        part_configuration["gender"],
    )
            print(_progress_bar(i, total))
            continue
        make_part(part_configuration)
        print(_progress_bar(i, total))

    print("Finished rendering all parts in family.")


if __name__ == "__main__":
    main()
