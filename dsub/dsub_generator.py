"""
dsub_dimensions.py
===================

Programmatic access to D-subminiature (MIL-DTL-24308) connector shell
dimensions, sourced from a manufacturer's published mechanical drawings.

PRIMARY SOURCE
--------------
Amphenol Pcd, "D-Sub Connectors" catalog (MIL-DTL-24308), Dec. 2018.
Retrieved via Mouser: https://www.mouser.com/datasheet/2/18/1/DSUB_2018-1651582.pdf
Pages 16-21: dimension tables for
    p16 - Standard Density Crimp   - Receptacle
    p17 - High     Density Crimp   - Receptacle
    p18 - Standard Density Crimp   - Plug
    p19 - High     Density Crimp   - Plug
    p20 - Standard Density Solder Cup - Receptacle
    p21 - Standard Density Solder Cup - Plug
Each page gives an "A" through "L" lettered dimension table per shell size,
per the source's own note: "Dimensions A-L: Top # = min., Bottom # = max."

CROSS-VALIDATION (used to confirm which letter means what, since the PDF
was read via OCR rather than viewed as a rendered image):
  - ITT Cannon / DigiKey "D Subminiature Full Line Catalog"
    https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/1364/d-sub_full_line_catalog.pdf
    Gave an independent front-face A-E table that matched Amphenol's A-E
    columns almost exactly, and separately gave solder-cup "MAX" depth
    call-outs (10.72mm plug / 9.91mm receptacle) used to sanity-check the
    depth-axis dimensions.
  - Positronic Catalog C-001 (MD/ED/SD/HDC/RD/ODD series)
    https://www.connectpositronic.com/wp-content/uploads/2023/04/C001Rev13_DSub.pdf
    Independently confirmed the same A-E front-face envelope values, and
    gave the insulator material/color call-outs used for
    `insulator_color` below (glass-filled polyester, UL94V-0, black;
    green DAP specifically on the military Rhapso-D line).
  - RS PRO product listing (RS Online, part 5443749 and similar)
    Used once, early on, to confirm which catalog letter corresponds to
    physical "depth" (front-to-back, mating axis) vs "height" (front-face,
    vertical axis) -- the two are easy to confuse from a table alone.

WHAT EACH LETTER MEANS (established by cross-referencing three sources'
diagrams/tables against each other; nothing here is a guess made in
isolation -- see the notes above for how each was confirmed):
    A - overall shell length, incl. mounting ears (along the pin row)
    B - shell body width, excl. mounting ears (along the pin row)
    C - mounting hole spacing (screw-to-screw)
    D - shell body height, excl. mounting ears (short axis)
    E - overall height, incl. mounting ears (short axis)
    F - side-view dimension drawn next to E (not a mating-axis length).
        Earlier envelopes used F as shroud depth; that doubled the
        front-to-back stack because MAX is already the overall length.
    G - front-of-shell length on the side view, labeled "G 09 TO 37 PIN"
        (~5.8-6.3mm). This is the mating shroud. Shell 5's tabulated G
        is the 3-row height, not a depth -- do not use it as shroud.
    H - a dimension that scales with shell size roughly in proportion to
        B, not to A or F. Earlier drafts of this dataset assumed H was
        the rear (cable-side) insulator depth -- checking the ratio
        H/B (~1.05-1.18, roughly constant) vs H/A (0.63-0.83, not
        constant) across all five/six shell sizes showed this is WRONG:
        H tracks the B (width) axis, not any front-to-back depth axis.
        It is most likely a width-adjacent dimension for an optional
        hardware configuration (e.g. a float-mount bracket) rather than
        a depth. Included for completeness but NOT mapped to
        `cable_side_depth` below -- that field is left as None pending a
        proper visual read of the drawing (see LIMITATIONS).
    J - did not vary across shell sizes in any of the six source tables
        (only ever restated for shell 1); modeled as a true constant.
    K - a small mounting-hardware dimension for shells 1-4, jumping by
        roughly 10x for shells 5-6 (50/104-pin), consistent across every
        table that reports it -- accepted as read, not flagged.
    L - a small edge/chamfer-scale dimension. Never restated by the
        source past shell 3, so modeled as constant beyond that point
        (see JUDGMENT CALLS).
    MAX_total_depth - side-view "11.23 MAX" / "9.91 MAX" overall length
        along the mating axis (not a rear-only segment). 9.91mm for
        solder-cup receptacles; 11.23mm for solder-cup plugs on shells
        1-4; 9.91mm for the 50-pin/3-row plug. Crimp has no MAX; J
        (~10.7mm, constant) is the same class of overall-depth stand-in.

JUDGMENT CALLS (made where the OCR'd source text was ambiguous or
incomplete; the user accepted these as final rather than requiring a
by-hand visual re-check of the PDF -- see conversation history if you
need to revisit one):
  1. Standard-density crimp PLUG, shell 1, dimension D: source text gave
     "8.23-8.23" (no spread), almost certainly an OCR/transcription gap.
     Corrected to 8.23-8.48mm to match the high-density plug's shell-1 D,
     since shell 1's outer envelope should not depend on contact density.
  2. K vs L, shells 3-4: receptacle K (0.74-1.25mm) and plug K
     (1.27-1.78mm) genuinely differ in the source and were kept as-read
     (plausible: socket vs. pin shells can need different hole/tab
     geometry there). L was standardized to 0.74-1.25mm for both genders
     at shells 3-4, since two independent plug tables agreed on it and no
     receptacle table contradicted it.
  3. J: never restated past shell 1 in any of six tables -> modeled as a
     constant (10.46-10.97mm) for every shell size and gender.
  4. L, shells 5-6: never given anywhere in the source. Modeled as
     constant at the shell-3/4 value (0.74-1.25mm) on the reasoning that
     L behaves like a small fixed machining feature (e.g. an edge break),
     unlike K, which clearly scales with shell size in every table that
     reports it.
  5. F/G, standard-density RECEPTACLE, shell 5: missing from source for
     the receptacle specifically. Filled from the shell-5 PLUG values
     (F=11.07-11.33mm, G=14.99-15.75mm), which were internally consistent
     across two independent plug tables (crimp and solder-cup) -- best
     available proxy, not an independent receptacle measurement.
  6. Solder-cup MAX_total_depth conflict: the source text contained two
     different "MAX" call-outs near the plug drawing (11.23mm and
     9.91mm). Resolved by shell size rather than discarding one: 11.23mm
     for shells 1-4 (matches a "SEE NOTE 1" annotation in the source),
     9.91mm for shell 5 specifically (matches a distinct "50 PIN (3 ROWS)"
     annotation, and also matches the receptacle's flat 9.91mm -- physically
     plausible that plug and receptacle depth converge at the largest
     shell size).

LIMITATIONS -- READ BEFORE TRUSTING A NUMBER FOR MANUFACTURING
----------------------------------------------------------------
  - This entire dataset was built from OCR'd/extracted TEXT off a PDF,
    not from a visually-inspected rendering of the drawing. Column
    assignment (which letter = which physical dimension) was inferred by
    cross-referencing three catalogs and checking numeric ratios, not by
    looking at the actual diagram. It has held together consistently,
    but "consistent" is not the same guarantee as "confirmed by eye."
  - `cable_side_depth` and `flange_thickness`, both requested by the user
    as parameters of interest, are NOT reliably present in this dataset.
    `flange_thickness` has no clean candidate letter at all. See the "H"
    note above for why `cable_side_depth` specifically was left unmapped
    rather than populated with a wrong-but-plausible-looking number.
  - Tolerances are given as published min-max ranges in millimeters. No
    unit conversion errors are expected (source gives mm primary, inch
    secondary; mm values were used throughout) but this has not been
    independently re-derived from the inch column.
  - Values are for MIL-DTL-24308 shells specifically; commercial-grade
    D-sub shells from other manufacturers may differ slightly (the
    DigiKey/Positronic cross-checks suggest differences are usually
    <0.5mm, but that was only spot-checked on the A-E envelope, not on
    F/G/H/J/K/L).

GLENAIR CROSS-CHECK (2026-08-19) — every shell × gender × density
------------------------------------------------------------------
Source (downloaded 2026-08-19):
  Glenair, "HiPer-D® M24308 Connectors and Accessories" (Series 28
  catalog PDF). U.S. CAGE 06324.
  URL: https://www.glenair.com/catalogs/hiper-d-connectors-and-accessories.pdf
  CDN mirror used during the check:
  https://cdn.glenair.com/catalogs/hiper-d-connectors-and-accessories.pdf
  Product family: machined aluminum HiPer-D® — intermateable /
  intermountable with stamped MIL-DTL-24308, not a drop-in dimensional
  clone of the Amphenol Pcd stamped shell.

Tables read from that catalog (catalog section B page footers):
  - 280-019S socket / receptacle, standard M24308-type flange — face
    dims A–G, shells 1–6 (catalog ~B-10; includes SD/HD insert rows)
  - 280-086P pin / plug, standard M24308-type flange + banding porch —
    face dims A–J, shells 1–6 (catalog ~B-19 / 280-086P DIMENSIONS)
  - 280-018P pin face table (A–G) was consulted only to confirm letter
    roles; the 280-086P A–J table was the plug numeric source for the
    shell-by-shell Δ below.
  Hermetic CODE RED 287-* sheets (e.g. 287-500 / 287-587 on
  https://www.glenair.com/hermetic-connectors/mil-dtl-24308/) use a
  different letter stack and were NOT used as the M24308 envelope
  reference.

IMPORTANT: Glenair HiPer-D figure letters are NOT the same letters as the
Amphenol Pcd A–L table that feeds this module. Remap before comparing:

    Our (Amphenol) letter     Glenair HiPer-D letter     Physical meaning
    ------------------------  -------------------------  ---------------------
    A                         A                          overall length + ears
    E                         B                          flange height (short)
    C                         C                          mounting-hole spacing
    B                         D                          shell body width
    D                         E (rcpt) / F (plug 086P)   shell body height
    J (overall depth stand-in) G (rcpt) / J (plug 086P)  mating-axis depth*

*HiPer-D is a thicker machined product; depth letters are not expected to
match stamped M24308 / Amphenol J exactly.

Method: for every variant this generator emits (Crimp×Plug/Receptacle×
Standard/High×shells 1–6, and Solder Cup×Standard where present), take
Amphenol midpoints and subtract the Glenair mm column after the remap
above.

Front-face results (A / E↔B / C / B↔D / D↔E|F):
  - Shells 1–4, all densities & genders: |Δ| ≤ 0.05 mm on A, B, C, D, E.
    Effectively exact agreement on the mating-face envelope.
  - Shell 5–6 receptacles: A/B/C/D/E likewise within 0.05 mm of Glenair
    (including the taller 50/78/104-pin flange E = 15.37 / 16.97 mm).
  - Shell 5–6 plugs: Amphenol (and this module) keep plug E = 12.55 mm
    and D = 8.355 mm — the same short-axis values as shells 1–4.
    Glenair HiPer-D plugs grow E/B and D/F with the 3-row shells
    (Δ ≈ −2.8 mm on shell 5, −4.4 mm on shell 6). That is a stamped-vs-
    machined / catalog-family difference, not an OCR error in our A–E
    table. Envelope code uses our Amphenol plug values as published.

Depth (our J vs Glenair G/J):
  - Our J is a constant 10.46–10.97 mm mid ≈ 10.715 mm (Amphenol crimp /
    solder tables). Glenair receptacle G ≈ 10.97 mm on shells 1–4
    (Δ ≈ −0.26 mm) and 13.56 / 15.14 mm on shells 5–6 (Δ ≈ −2.8 / −4.4 mm
    because our J never steps up). Glenair plug J ≈ 11.73 mm on shells
    1–4 (Δ ≈ −1.0 mm). Do NOT “fix” our J to HiPer-D — stamped
    M24308 overall depth is the Amphenol/ITT/Positronic figure this
    library targets; HiPer-D is deliberately thicker.

Letters not cross-checked to Glenair face tables:
  - Our F, G, H, K, L (Amphenol side-view / hardware letters) do not
    share names or roles with HiPer-D F/G/H. G-as-shroud for shells 1–4
    (~5.8–6.3 mm) remains an Amphenol-side-view read; Glenair’s G is
    overall depth. No Glenair cell was used to overwrite F/G/H/K/L.

Solder-cup MAX_total_depth (9.91 / 11.23 mm): no Glenair HiPer-D
equivalent in the face tables above; left on the Amphenol/ITT read.

Bottom line: every M24308 front-face envelope this library emits for
shells 1–4 matches Glenair HiPer-D after letter remap. Shells 5–6
receptacles match; plugs keep Amphenol’s shorter flange/body height.
Mating-axis depth stays on the stamped-shell (Amphenol) J/MAX figures.

USAGE
-----
    from dsub_dimensions import get_dimension, list_variants

    # Get dimension "A" for a standard-density crimp receptacle, 25-pin,
    # as a (min, max) tuple in mm:
    get_dimension("Crimp", "Receptacle", "Standard", pin_count=25, dim="A")
    # -> (52.65, 53.42)

    # Same, but get the midpoint as a single float:
    get_dimension("Crimp", "Receptacle", "Standard", pin_count=25,
                  dim="A", agg="mid")
    # -> 53.035

    # Look up by shell number instead of pin count:
    get_dimension("Solder Cup", "Plug", "Standard", shell_no=3, dim="MAX_total_depth")
    # -> (11.23, 11.23)
"""

import csv
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional, Union, Literal

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

Aggregation = Literal["range", "min", "max", "mid"]

DIMENSION_LETTERS = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "J",
    "K",
    "L",
    "MAX_total_depth",
]


@dataclass(frozen=True)
class ShellVariant:
    page: int
    connector_type: str  # "Crimp" or "Solder Cup"
    gender: str  # "Plug" or "Receptacle"
    density: str  # "Standard" or "High"
    shell_no: int
    pin_count: int
    dims: dict  # letter -> (min_mm, max_mm) or None
    resolution_note: str = ""


def _r(spec: Optional[str]):
    """Parse a 'min-max' string into a (min, max) float tuple, or None."""
    if not spec:
        return None
    lo, hi = spec.split("-")
    return (float(lo), float(hi))


# ---------------------------------------------------------------------------
# The dataset itself. One row per connector variant, transcribed from
# Amphenol Pcd catalog pages 16-21 (see module docstring for citations and
# the full list of judgment calls applied to fill gaps in the source text).
# ---------------------------------------------------------------------------
_ROWS = [
    # page, conn_type,     gender,       density,    shell, pins,
    #   A,               B,               C,               D,              E,
    #   F,               G,               H,                J,               K,               L,             MAX_depth, note
    (
        16,
        "Crimp",
        "Receptacle",
        "Standard",
        1,
        9,
        "30.43-31.19",
        "16.21-16.46",
        "24.87-25.12",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "19.02-19.53",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        None,
        "source",
    ),
    (
        16,
        "Crimp",
        "Receptacle",
        "Standard",
        2,
        15,
        "38.76-39.52",
        "24.54-24.79",
        "33.20-33.45",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "27.25-27.76",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        None,
        "D/E/F/G/J/K/L inherited from shell 1",
    ),
    (
        16,
        "Crimp",
        "Receptacle",
        "Standard",
        3,
        25,
        "52.65-53.42",
        "38.25-38.51",
        "46.91-47.17",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "41.02-41.53",
        "10.46-10.97",
        "0.74-1.25",
        "0.74-1.25",
        None,
        "D/E/F/G/J from shell1; K,L per shell3-4 step (source)",
    ),
    (
        16,
        "Crimp",
        "Receptacle",
        "Standard",
        4,
        37,
        "68.94-69.70",
        "54.71-54.97",
        "63.37-63.63",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "57.45-57.96",
        "10.46-10.97",
        "0.74-1.25",
        "0.74-1.25",
        None,
        "D/E/F/G/J from shell1; K,L per shell3-4 step (source)",
    ),
    (
        16,
        "Crimp",
        "Receptacle",
        "Standard",
        5,
        50,
        "66.55-67.31",
        "52.30-52.55",
        "60.99-61.24",
        "10.62-10.87",
        "14.99-15.75",
        "11.07-11.33",
        "14.99-15.75",
        "55.07-55.58",
        "10.46-10.97",
        "13.31-13.82",
        "0.74-1.25",
        None,
        "F,G proxied from plug shell5; J constant; L carried from shell3-4",
    ),
    (
        17,
        "Crimp",
        "Receptacle",
        "High",
        1,
        15,
        "30.43-31.19",
        "16.21-16.46",
        "24.87-25.12",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "19.02-19.53",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        None,
        "source",
    ),
    (
        17,
        "Crimp",
        "Receptacle",
        "High",
        2,
        26,
        "38.76-39.52",
        "24.54-24.79",
        "33.20-33.45",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "27.25-27.76",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        None,
        "inherited from shell1",
    ),
    (
        17,
        "Crimp",
        "Receptacle",
        "High",
        3,
        44,
        "52.65-53.42",
        "38.25-38.51",
        "46.91-47.17",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "41.02-41.53",
        "10.46-10.97",
        "0.74-1.25",
        "0.74-1.25",
        None,
        "D/E/F/G/J from shell1; K,L per shell3-4 step",
    ),
    (
        17,
        "Crimp",
        "Receptacle",
        "High",
        4,
        62,
        "68.94-69.70",
        "54.71-54.97",
        "63.37-63.63",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "57.45-57.96",
        "10.46-10.97",
        "0.74-1.25",
        "0.74-1.25",
        None,
        "D/E/F/G/J from shell1; K,L per shell3-4 step",
    ),
    (
        17,
        "Crimp",
        "Receptacle",
        "High",
        5,
        78,
        "66.55-67.31",
        "52.30-52.55",
        "60.99-61.24",
        "10.62-10.87",
        "14.99-15.75",
        "11.07-11.33",
        "14.99-15.75",
        "55.07-55.58",
        "10.46-10.97",
        "13.31-13.82",
        "0.74-1.25",
        None,
        "F,G proxied from plug shell5; J constant; L carried",
    ),
    (
        17,
        "Crimp",
        "Receptacle",
        "High",
        6,
        104,
        "68.94-69.70",
        "55.47-55.73",
        "63.37-63.63",
        "12.19-12.45",
        "16.59-17.35",
        "12.65-12.90",
        "16.59-17.35",
        "58.22-58.72",
        "10.46-10.97",
        "14.88-15.39",
        "0.74-1.25",
        None,
        "F,G proxied from plug shell6; J constant; L carried",
    ),
    (
        18,
        "Crimp",
        "Plug",
        "Standard",
        1,
        9,
        "30.43-31.19",
        "16.79-17.04",
        "24.87-25.12",
        "8.23-8.48",
        "12.17-12.93",
        "10.46-10.97",
        "5.82-6.12",
        "19.02-19.53",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        None,
        "D corrected to match High-Density Plug shell1 (same outer shell)",
    ),
    (
        18,
        "Crimp",
        "Plug",
        "Standard",
        2,
        15,
        "38.76-39.52",
        "25.12-25.37",
        "33.20-33.45",
        "8.23-8.48",
        "12.17-12.93",
        "10.46-10.97",
        "5.82-6.12",
        "27.25-27.76",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        None,
        "inherited from shell1",
    ),
    (
        18,
        "Crimp",
        "Plug",
        "Standard",
        3,
        25,
        "52.65-53.42",
        "38.84-39.09",
        "46.91-47.17",
        "8.23-8.48",
        "12.17-12.93",
        "10.57-11.07",
        "5.69-5.99",
        "41.02-41.53",
        "10.46-10.97",
        "1.27-1.78",
        "0.74-1.25",
        None,
        "D/E/J from shell1; F,G,H,K per source; L per shell3-4 step",
    ),
    (
        18,
        "Crimp",
        "Plug",
        "Standard",
        4,
        37,
        "68.94-69.70",
        "55.30-55.55",
        "63.37-63.63",
        "8.23-8.48",
        "12.17-12.93",
        "10.57-11.07",
        "5.69-5.99",
        "57.45-57.96",
        "10.46-10.97",
        "1.27-1.78",
        "0.74-1.25",
        None,
        "D/E/J from shell1; F,G,K carried from shell3; L per step",
    ),
    (
        18,
        "Crimp",
        "Plug",
        "Standard",
        5,
        50,
        "66.55-67.31",
        "52.68-52.93",
        "60.99-61.24",
        "8.23-8.48",
        "12.17-12.93",
        "11.07-11.33",
        "14.99-15.75",
        "55.07-55.58",
        "10.46-10.97",
        "13.31-13.82",
        "0.74-1.25",
        None,
        "D,J inherited/constant; L carried",
    ),
    (
        19,
        "Crimp",
        "Plug",
        "High",
        1,
        15,
        "30.43-31.19",
        "16.79-17.04",
        "24.87-25.12",
        "8.23-8.48",
        "12.17-12.93",
        "10.64-10.97",
        "5.82-6.12",
        "19.02-19.53",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        None,
        "source",
    ),
    (
        19,
        "Crimp",
        "Plug",
        "High",
        2,
        26,
        "38.76-39.52",
        "25.12-25.37",
        "33.20-33.45",
        "8.23-8.48",
        "12.17-12.93",
        "10.64-10.97",
        "5.82-6.12",
        "27.25-27.76",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        None,
        "inherited from shell1",
    ),
    (
        19,
        "Crimp",
        "Plug",
        "High",
        3,
        44,
        "52.65-53.42",
        "38.84-39.09",
        "46.91-47.17",
        "8.23-8.48",
        "12.17-12.93",
        "10.57-11.07",
        "5.69-5.99",
        "41.02-41.53",
        "10.46-10.97",
        "1.27-1.78",
        "0.74-1.25",
        None,
        "source (D/E/J inherited)",
    ),
    (
        19,
        "Crimp",
        "Plug",
        "High",
        4,
        62,
        "68.94-69.70",
        "55.30-55.55",
        "63.37-63.63",
        "8.23-8.48",
        "12.17-12.93",
        "10.57-11.07",
        "5.69-5.99",
        "57.45-57.96",
        "10.46-10.97",
        "1.27-1.78",
        "0.74-1.25",
        None,
        "D/E/J inherited; F,G,K carried from shell3",
    ),
    (
        19,
        "Crimp",
        "Plug",
        "High",
        5,
        78,
        "66.55-67.31",
        "52.68-52.93",
        "60.99-61.24",
        "8.23-8.48",
        "12.17-12.93",
        "11.07-11.33",
        "14.99-15.75",
        "55.07-55.58",
        "10.46-10.97",
        "13.31-13.82",
        "0.74-1.25",
        None,
        "source (D,J inherited/constant; L carried)",
    ),
    (
        19,
        "Crimp",
        "Plug",
        "High",
        6,
        104,
        "68.94-69.70",
        "56.06-56.31",
        "63.37-63.63",
        "8.23-8.48",
        "12.17-12.93",
        "12.65-12.90",
        "16.59-17.35",
        "58.22-58.72",
        "10.46-10.97",
        "14.88-15.39",
        "0.74-1.25",
        None,
        "source (D,J inherited/constant; L carried)",
    ),
    (
        20,
        "Solder Cup",
        "Receptacle",
        "Standard",
        1,
        9,
        "30.43-31.19",
        "16.21-16.46",
        "24.87-25.12",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "19.02-19.53",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        "9.91-9.91",
        "source",
    ),
    (
        20,
        "Solder Cup",
        "Receptacle",
        "Standard",
        2,
        15,
        "38.76-39.52",
        "24.54-24.79",
        "33.20-33.45",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "27.25-27.76",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        "9.91-9.91",
        "inherited from shell1",
    ),
    (
        20,
        "Solder Cup",
        "Receptacle",
        "Standard",
        3,
        25,
        "52.65-53.42",
        "38.25-38.51",
        "46.91-47.17",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "41.02-41.53",
        "10.46-10.97",
        "0.74-1.25",
        "0.74-1.25",
        "9.91-9.91",
        "D/E/F/G/J from shell1; K,L per shell3-4 step",
    ),
    (
        20,
        "Solder Cup",
        "Receptacle",
        "Standard",
        4,
        37,
        "68.94-69.70",
        "54.71-54.97",
        "63.37-63.63",
        "7.67-8.03",
        "12.17-12.93",
        "10.64-11.15",
        "6.05-6.30",
        "57.45-57.96",
        "10.46-10.97",
        "0.74-1.25",
        "0.74-1.25",
        "9.91-9.91",
        "D/E/F/G/J from shell1; K,L per shell3-4 step",
    ),
    (
        20,
        "Solder Cup",
        "Receptacle",
        "Standard",
        5,
        50,
        "66.55-67.31",
        "52.30-52.55",
        "60.99-61.24",
        "10.62-10.87",
        "14.99-15.75",
        "11.07-11.33",
        "14.99-15.75",
        "55.07-55.58",
        "10.46-10.97",
        "13.31-13.82",
        "0.74-1.25",
        "9.91-9.91",
        "F,G proxied from plug shell5; J constant; L carried",
    ),
    (
        21,
        "Solder Cup",
        "Plug",
        "Standard",
        1,
        9,
        "30.43-31.19",
        "16.79-17.04",
        "24.87-25.12",
        "8.23-8.48",
        "12.17-12.93",
        "10.46-10.97",
        "5.82-6.05",
        "19.02-19.53",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        "11.23-11.23",
        "source",
    ),
    (
        21,
        "Solder Cup",
        "Plug",
        "Standard",
        2,
        15,
        "38.76-39.52",
        "25.12-25.37",
        "33.20-33.45",
        "8.23-8.48",
        "12.17-12.93",
        "10.46-10.97",
        "5.82-6.05",
        "27.25-27.76",
        "10.46-10.97",
        "0.89-1.52",
        "0.51-1.02",
        "11.23-11.23",
        "inherited from shell1",
    ),
    (
        21,
        "Solder Cup",
        "Plug",
        "Standard",
        3,
        25,
        "52.65-53.42",
        "38.84-39.09",
        "46.91-47.17",
        "8.23-8.48",
        "12.17-12.93",
        "10.57-11.07",
        "5.69-5.99",
        "41.02-41.53",
        "10.46-10.97",
        "1.27-1.78",
        "0.74-1.24",
        "11.23-11.23",
        "D/E/J from shell1; F,G,H,K,L per source",
    ),
    (
        21,
        "Solder Cup",
        "Plug",
        "Standard",
        4,
        37,
        "68.94-69.70",
        "55.30-55.55",
        "63.37-63.63",
        "8.23-8.48",
        "12.17-12.93",
        "10.57-11.07",
        "5.69-5.99",
        "57.45-57.96",
        "10.46-10.97",
        "1.27-1.78",
        "0.74-1.24",
        "11.23-11.23",
        "D/E/J from shell1; F,G,K carried from shell3",
    ),
    (
        21,
        "Solder Cup",
        "Plug",
        "Standard",
        5,
        50,
        "66.55-67.31",
        "52.68-52.93",
        "60.99-61.24",
        "8.23-8.48",
        "12.17-12.93",
        "11.07-11.33",
        "14.99-15.75",
        "55.07-55.58",
        "10.46-10.97",
        "13.31-13.82",
        "0.74-1.24",
        "9.91-9.91",
        "D,J inherited/constant; L carried; MAX depth uses the 50-pin/3-row "
        "note (9.91) rather than the 09-37 pin note (11.23)",
    ),
]


def _build_variants():
    variants = []
    for row in _ROWS:
        (
            page,
            ctype,
            gender,
            density,
            shell_no,
            pins,
            A,
            B,
            C,
            D,
            E,
            F,
            G,
            H,
            J,
            K,
            L,
            maxd,
            note,
        ) = row
        dims = {
            "A": _r(A),
            "B": _r(B),
            "C": _r(C),
            "D": _r(D),
            "E": _r(E),
            "F": _r(F),
            "G": _r(G),
            "H": _r(H),
            "J": _r(J),
            "K": _r(K),
            "L": _r(L),
            "MAX_total_depth": _r(maxd),
        }
        variants.append(
            ShellVariant(page, ctype, gender, density, shell_no, pins, dims, note)
        )
    return variants


_VARIANTS = _build_variants()


def _normalize(s: str) -> str:
    return s.strip().lower().replace("_", " ")


def _matches(
    v: ShellVariant, connector_type, gender, density, shell_no, pin_count
) -> bool:
    if connector_type is not None and _normalize(v.connector_type) != _normalize(
        connector_type
    ):
        return False
    if gender is not None and _normalize(v.gender) != _normalize(gender):
        return False
    if density is not None and _normalize(v.density) != _normalize(density):
        return False
    if shell_no is not None and v.shell_no != shell_no:
        return False
    if pin_count is not None and v.pin_count != pin_count:
        return False
    return True


def find_variant(
    connector_type: str,
    gender: str,
    density: str,
    shell_no: Optional[int] = None,
    pin_count: Optional[int] = None,
) -> ShellVariant:
    """
    Locate a single ShellVariant. Identify the shell either by shell_no
    (1-6) or pin_count (e.g. 9, 15, 25, 37, 50, 78, 104) -- provide
    exactly one of the two.

    Raises ValueError if zero or more than one row matches (e.g. if
    density is ambiguous for a shell/pin_count that exists in both
    Standard and High density -- pin_count alone disambiguates this in
    practice since Standard and High density use different pin counts
    for the same shell_no).
    """
    if (shell_no is None) == (pin_count is None):
        raise ValueError("Provide exactly one of shell_no or pin_count.")

    matches = [
        v
        for v in _VARIANTS
        if _matches(v, connector_type, gender, density, shell_no, pin_count)
    ]
    if not matches:
        raise ValueError(
            f"No variant found for connector_type={connector_type!r}, "
            f"gender={gender!r}, density={density!r}, "
            f"shell_no={shell_no!r}, pin_count={pin_count!r}. "
            f"Call list_variants() to see everything available."
        )
    if len(matches) > 1:
        raise ValueError(
            f"{len(matches)} variants matched -- request is ambiguous. "
            f"Matches: {[(m.connector_type, m.gender, m.density, m.shell_no, m.pin_count) for m in matches]}"
        )
    return matches[0]


def get_dimension(
    connector_type: str,
    gender: str,
    density: str,
    dim: str,
    shell_no: Optional[int] = None,
    pin_count: Optional[int] = None,
    agg: Aggregation = "range",
) -> Union[tuple, float, None]:
    """
    Return a dimension for a specific D-sub shell variant.

    Parameters
    ----------
    connector_type : "Crimp" or "Solder Cup"
    gender          : "Plug" or "Receptacle"
    density         : "Standard" or "High"
    dim             : one of A,B,C,D,E,F,G,H,J,K,L,MAX_total_depth
                       (see module docstring for what each letter means,
                       and its LIMITATIONS section for which ones are
                       well-confirmed vs. best-effort)
    shell_no        : 1-6 (provide this OR pin_count, not both)
    pin_count       : 9,15,25,37,50,26,44,62,78,104 (provide this OR shell_no)
    agg             : "range" (default) -> (min_mm, max_mm) tuple
                       "min"  -> just the minimum
                       "max"  -> just the maximum
                       "mid"  -> midpoint float, (min+max)/2

    Returns None if the requested dimension isn't defined for that variant
    (e.g. MAX_total_depth is only defined for Solder Cup connectors).

    Example
    -------
    >>> get_dimension("Crimp", "Receptacle", "Standard", "A", pin_count=25)
    (52.65, 53.42)
    >>> get_dimension("Crimp", "Receptacle", "Standard", "A", pin_count=25, agg="mid")
    53.035
    """
    if dim not in DIMENSION_LETTERS:
        raise ValueError(
            f"Unknown dimension {dim!r}. Valid options: {DIMENSION_LETTERS}"
        )

    variant = find_variant(connector_type, gender, density, shell_no, pin_count)
    value = variant.dims.get(dim)
    if value is None:
        return None

    lo, hi = value
    if agg == "range":
        return (lo, hi)
    elif agg == "min":
        return lo
    elif agg == "max":
        return hi
    elif agg == "mid":
        return (lo + hi) / 2.0
    else:
        raise ValueError(f"Unknown agg {agg!r}. Use 'range', 'min', 'max', or 'mid'.")


def get_resolution_note(
    connector_type: str,
    gender: str,
    density: str,
    shell_no: Optional[int] = None,
    pin_count: Optional[int] = None,
) -> str:
    """
    Return the provenance note for a variant -- says whether each row's
    values came straight from the source or were filled in via one of the
    documented judgment calls (see module docstring).
    """
    return find_variant(
        connector_type, gender, density, shell_no, pin_count
    ).resolution_note


def list_variants():
    """Return every (connector_type, gender, density, shell_no, pin_count) combo available."""
    return [
        (v.connector_type, v.gender, v.density, v.shell_no, v.pin_count)
        for v in _VARIANTS
    ]


# ---------------------------------------------------------------------------
# Part family generator (same pipeline as D38999/d38999_generator.py)
# ---------------------------------------------------------------------------
# Official PIN: M24308/{slash}-{dash}{finish}  e.g. M24308/2-3F
# Library PN:   M24308_{slash}-{dash}{finish}  e.g. M24308_2-3F
#   (slash after the spec name becomes underscore, same as D38999_)
#
#   slash 1 = solder-cup receptacle (socket), Class G
#   slash 2 = crimp receptacle (socket), Class G
#   slash 3 = solder-cup plug (pin), Class G
#   slash 4 = crimp plug (pin), Class G
#   dash   = shell_no for Standard density; shell_no+10 for High density
#            (Class G, no float mount — Amphenol Pcd 2018 QPL listing)
#   finish letters from MIL-DTL-24308 Class G:
#     A = pure electrodeposited aluminum
#     F = cadmium
#     K = zinc nickel
#     T = nickel fluorocarbon polymer
#     Z = zinc
# ---------------------------------------------------------------------------

REVISION = "1"
DATE_STARTED = "8/16/26"
delete_pngs = True

PX_PER_IN = 96.0
MM_PER_IN = 25.4
# Flange thickness is not a mapped A-L letter (see module LIMITATIONS).
# 1.25 mm is a drawing-only estimate so the side silhouette has a step.
FLANGE_THICKNESS_MM = 1.25

SLASH_SHEETS = {
    ("Solder Cup", "Receptacle"): "1",
    ("Crimp", "Receptacle"): "2",
    ("Solder Cup", "Plug"): "3",
    ("Crimp", "Plug"): "4",
}

# IEC 60807 / DIN 41652 shell letters (size 6 has no classic letter).
SHELL_LETTERS = {1: "E", 2: "A", 3: "B", 4: "C", 5: "D", 6: ""}

# MIL-DTL-24308 Class G finish suffixes (P is Class N only).
FINISHES = {
    "A": "pure electrodeposited aluminum",
    "F": "cadmium",
    "K": "zinc nickel",
    "T": "nickel fluorocarbon polymer",
    "Z": "zinc",
}

CONTACT_SIZES = {
    "20": {
        "awg_min": 20,
        "awg_max": 26,
        "current_rating": 7.5,
        "crimp_tool": "M22520/2-01",
        "extraction_tool": "M81969/14-01",
    },
    "22": {
        "awg_min": 22,
        "awg_max": 28,
        "current_rating": 5.0,
        "crimp_tool": "M22520/2-01",
        "extraction_tool": "M81969/39-01",
    },
}

# Flagnotes sit on a circle centered at the cable-side origin, 15 deg
# apart, alternating up/down from due-right like D38999. Notes left of
# the mating face are omitted. Leader destinations are spaced evenly
# along the mating-face outline (shroud height).
FLAGNOTE_CENTER_X_IN = 0.0
FLAGNOTE_CENTER_Y_IN = 0.0
FLAGNOTE_RADIUS_IN = 3.0
FLAGNOTE_ANGLES_DEG = (
    0, 15, -15, 30, -30, 45, -45, 60, -60, 75, -75, 90, -90
)


def _flagnote_note_polar(theta_deg):
    """Angle/distance from the flagnote center, clamped to x >= 0."""
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
    """Center-out stations from -half_h to +half_h (0, +step, -step, ...)."""
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
        note_x = (
            FLAGNOTE_CENTER_X_IN
            + note_dist * math.cos(math.radians(note_angle))
        )
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


def _mid(rng):
    if rng is None:
        return None
    return (rng[0] + rng[1]) / 2.0


def _px_mm(mm):
    return (mm / MM_PER_IN) * PX_PER_IN


def _poly(points, fill="#C0C0C0"):
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}" stroke="black" stroke-width="1"/>'


def contact_size_for(density):
    return "20" if density == "Standard" else "22"


def dash_number(density, shell_no):
    if density == "High":
        return shell_no + 10
    return shell_no


def slash_sheet(connector_type, gender):
    try:
        return SLASH_SHEETS[(connector_type, gender)]
    except KeyError:
        raise ValueError(
            f"No MIL-DTL-24308 slash sheet for "
            f"connector_type={connector_type!r}, gender={gender!r}."
        )


def official_pin(part_configuration):
    slash = slash_sheet(
        part_configuration["connector_type"], part_configuration["gender"]
    )
    dash = dash_number(
        part_configuration["density"], part_configuration["shell_no"]
    )
    return f"M24308/{slash}-{dash}{part_configuration['finish']}"


def common_name(part_configuration):
    letter = SHELL_LETTERS.get(part_configuration["shell_no"], "")
    pins = part_configuration["pin_count"]
    if letter:
        name = f"D{letter}-{pins}"
    else:
        name = f"HD-{pins}"
    if part_configuration["density"] == "High" and letter:
        name = f"{name} HD"
    if (
        part_configuration["shell_no"] == 1
        and part_configuration["density"] == "Standard"
    ):
        name = f"{name} (DB-9)"
    return name


def make_part_number(part_configuration):
    return official_pin(part_configuration).replace("M24308/", "M24308_", 1)


def variant_from_configuration(part_configuration):
    return find_variant(
        part_configuration["connector_type"],
        part_configuration["gender"],
        part_configuration["density"],
        shell_no=part_configuration["shell_no"],
    )


# G on the Amphenol side view is the 09–37 pin front-of-shell length.
# Tabulated G for 50-pin is the 3-row height (~15mm), not a depth.
_DSUB_SHROUD_DEPTH_MAX_MM = 8.0
_DSUB_SHROUD_FALLBACK_MM = 5.935  # shell-1 plug G midpoint


def mating_shroud_mm(variant):
    g = _mid(variant.dims.get("G"))
    if g is not None and g < _DSUB_SHROUD_DEPTH_MAX_MM:
        return g
    return _DSUB_SHROUD_FALLBACK_MM


def connector_depth_mm(variant):
    # MAX is the overall mating-axis length. Crimp uses constant J.
    maxd = _mid(variant.dims.get("MAX_total_depth"))
    if maxd is not None:
        return maxd
    j = _mid(variant.dims.get("J"))
    if j is not None:
        return j
    return _mid(variant.dims["F"])


def cable_side_mm(variant):
    rear = connector_depth_mm(variant) - FLANGE_THICKNESS_MM - mating_shroud_mm(variant)
    return max(rear, 1.0)


def dsub_connector_svg(part_number, variant):
    """
    Top/edge silhouette: origin at the cable side, +X toward the mating
    face (same convention as D38999).

    Stack-up matches the Amphenol side view, mirrored to this origin:
    insulator (remainder of MAX/J) | mounting flange | mating shroud (G).
    Vertical is A (ears) / B (body). D/E is into the page and not drawn.
    """
    a = _mid(variant.dims["A"])
    b = _mid(variant.dims["B"])
    cable_px = _px_mm(cable_side_mm(variant))
    flange_px = _px_mm(FLANGE_THICKNESS_MM)
    shroud_px = _px_mm(mating_shroud_mm(variant))
    flange_rear = cable_px
    flange_front = cable_px + flange_px
    mating_x = flange_front + shroud_px
    half_a = _px_mm(a) / 2.0
    half_b = _px_mm(b) / 2.0

    outline = [
        (0.0, -half_b),
        (flange_rear, -half_b),
        (flange_rear, -half_a),
        (flange_front, -half_a),
        (flange_front, -half_b),
        (mating_x, -half_b),
        (mating_x, half_b),
        (flange_front, half_b),
        (flange_front, half_a),
        (flange_rear, half_a),
        (flange_rear, half_b),
        (0.0, half_b),
    ]

    insulator = (
        f'<rect x="0.00" y="{-half_b:.2f}" '
        f'width="{cable_px:.2f}" height="{2 * half_b:.2f}" '
        f'fill="#2C2C2C" stroke="black" stroke-width="1"/>'
    )

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="400" height="400">
<g id="{part_number}-drawing-contents-start">
{_poly(outline)}
{insulator}
</g>
<g id="{part_number}-drawing-contents-end">
</g>
</svg>'''


DSUB_SIDE_TAPER_DEG = 12.0
_EPS = 1e-9


def _arc_yz(cx, cz, radius, a0, a1, n):
    pts = []
    for i in range(n + 1):
        t = a0 + (a1 - a0) * i / n
        pts.append((cx + radius * math.cos(t), cz + radius * math.sin(t)))
    return pts


def _fillet_vertex_yz(p0, p1, p2, radius, n):
    """Arc replacing corner p1 of a CCW YZ polygon."""
    y0, z0 = p0
    y1, z1 = p1
    y2, z2 = p2
    v1 = (y0 - y1, z0 - z1)
    v2 = (y2 - y1, z2 - z1)
    l1 = math.hypot(*v1)
    l2 = math.hypot(*v2)
    if l1 < _EPS or l2 < _EPS or radius < _EPS:
        return [p1]
    u1 = (v1[0] / l1, v1[1] / l1)
    u2 = (v2[0] / l2, v2[1] / l2)
    turn = math.atan2(u1[0] * u2[1] - u1[1] * u2[0], u1[0] * u2[0] + u1[1] * u2[1])
    half = abs(turn) / 2.0
    if half < 1e-6:
        return [p1]
    t = min(radius / math.tan(half), l1 * 0.45, l2 * 0.45)
    r = t * math.tan(half)
    t1 = (y1 + u1[0] * t, z1 + u1[1] * t)
    t2 = (y1 + u2[0] * t, z1 + u2[1] * t)
    bis = (u1[0] + u2[0], u1[1] + u2[1])
    bl = math.hypot(*bis)
    if bl < _EPS:
        return [t1, t2]
    dist = r / math.sin(half)
    cy = y1 + bis[0] / bl * dist
    cz = z1 + bis[1] / bl * dist
    a0 = math.atan2(t1[1] - cz, t1[0] - cy)
    a1 = math.atan2(t2[1] - cz, t2[0] - cy)
    sweep = a1 - a0
    while sweep <= 0.0:
        sweep += 2.0 * math.pi
    while sweep > 2.0 * math.pi:
        sweep -= 2.0 * math.pi
    return [
        (cy + r * math.cos(a0 + sweep * i / n), cz + r * math.sin(a0 + sweep * i / n))
        for i in range(n + 1)
    ]


def _rounded_rect_yz(width_mm, height_mm, radius_mm=None, n=6):
    """Flange plate in YZ: width = A (pin row), height = E (short axis)."""
    hw, hh = width_mm / 2.0, height_mm / 2.0
    r = min(
        radius_mm if radius_mm is not None else min(hw, hh) * 0.18,
        hw * 0.45,
        hh * 0.45,
    )
    if r < 0.05:
        return [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    pts = []
    pts += _arc_yz(hw - r, -hh + r, r, -math.pi / 2, 0.0, n)
    pts += _arc_yz(hw - r, hh - r, r, 0.0, math.pi / 2, n)
    pts += _arc_yz(-hw + r, hh - r, r, math.pi / 2, math.pi, n)
    pts += _arc_yz(-hw + r, -hh + r, r, math.pi, 3.0 * math.pi / 2, n)
    return pts


def _d_shell_yz(wide_mm, height_mm, n=8):
    """D-sub mating outline: isosceles trapezoid (wide at −Z), rounded corners."""
    inset = height_mm * math.tan(math.radians(DSUB_SIDE_TAPER_DEG))
    narrow = max(wide_mm - 2.0 * inset, wide_mm * 0.55)
    hw, hn, hh = wide_mm / 2.0, narrow / 2.0, height_mm / 2.0
    r = min(height_mm * 0.15, hw * 0.25, hn * 0.25)
    verts = [(-hw, -hh), (hw, -hh), (hn, hh), (-hn, hh)]
    pts = []
    m = len(verts)
    for i in range(m):
        pts.extend(
            _fillet_vertex_yz(
                verts[(i - 1) % m], verts[i], verts[(i + 1) % m], r, n
            )
        )
    return pts


def envelope_prisms_mm(variant):
    """Low-fi envelope from Amphenol A–G / MAX, in millimetres.

    Catalog front view (the photo) is the YZ plane, looking toward −X:
      A  flange length along the pin row     →  STEP ±Y
      B  shell width along the pin row       →  STEP ±Y
      C  mounting-hole spacing               →  not modelled
      D  shell height (short axis)           →  STEP ±Z
      E  flange height (short axis)          →  STEP ±Z
      G  mating-shroud depth (09–37 pin)     →  STEP +X, in front of the flange
      MAX / J  overall mating-axis length    →  STEP +X total
    +X is the cable/mating axis (same as D38999). FreeCAD Front is XZ (the
    side, ~square); the D-face is FreeCAD Right (YZ).
    """
    cable = cable_side_mm(variant)
    flange = FLANGE_THICKNESS_MM
    shroud = mating_shroud_mm(variant)
    shell = _d_shell_yz(_mid(variant.dims["B"]), _mid(variant.dims["D"]))
    plate = _rounded_rect_yz(_mid(variant.dims["A"]), _mid(variant.dims["E"]))
    x1 = cable
    x2 = cable + flange
    x3 = x2 + shroud
    return [
        (0.0, x1, shell),
        (x1, x2, plate),
        (x2, x3, shell),
    ]


# Plug STEP set-in (~standard D-sub mating engagement). Origin is the
# cable-side face (same as the drawing). Receptacle STEPs: solid mating face.
PIN_CAVITY_DEPTH_MM = 0.25 * MM_PER_IN
PIN_CAVITY_WALL_MM = (19.0 - 15.75) / 2.0


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


def mate_csys_3d(variant):
    """Mating face in the STEP frame (inches), identity orientation.

    Origin is the cable-side face; this output sits on the mating face.
    """
    from dsub_step_mating import face_x_mm, step_origin_x_mm as origin_x_mm

    segs = envelope_prisms_mm(variant)
    is_pin = str(variant.gender).lower() == "plug"
    origin_x = origin_x_mm(segs, is_pin, PIN_CAVITY_DEPTH_MM)
    return csys_6dof_mm(face_x_mm(segs) - origin_x, 0.0, 0.0)


def write_part_step(rev_dir, part_number, variant):
    """Write STEP with cable-side origin; plugs get a shallow set-in cup."""
    from dsub_step_mating import write_mating_prism_step

    path = os.path.join(rev_dir, f"{part_number}-rev{REVISION}-model.step")
    is_pin = str(variant.gender).lower() == "plug"
    gender = "pin" if is_pin else "socket"
    description = f"MIL-DTL-24308 low-fidelity envelope ({gender} mating face)"
    return write_mating_prism_step(
        step_utils,
        path,
        part_number,
        envelope_prisms_mm(variant),
        is_pin,
        PIN_CAVITY_DEPTH_MM,
        PIN_CAVITY_WALL_MM,
        description,
    )



# Typical QPL steel-shell masses (grams, contacts included). Aluminum finish A
# uses 0.58x. High-density adds 0.12 g per extra contact over the
# standard-density count of the same shell.
MASS_SOURCE = (
    "Typical QPL steel-shell masses by shell size, grams including contacts; "
    "not a single manufacturer weight table. Aluminum finish A is scaled 0.58x; "
    "high-density adds 0.12 g per extra contact over the standard-density count."
)
_DSUB_STEEL_G = {
    # shell_no: (plug, receptacle)
    1: (8.5, 8.0),
    2: (13.0, 12.2),
    3: (19.5, 18.2),
    4: (28.0, 26.0),
    5: (41.0, 38.0),
    6: (54.0, 50.0),
}
_DSUB_STD_PINS = {1: 9, 2: 15, 3: 25, 4: 37, 5: 50, 6: 104}
_DSUB_HD_PINS = {1: 15, 2: 26, 3: 44, 4: 62, 5: 78, 6: 104}


def part_mass_lbs(gender, density, shell_no, pin_count, finish):
    plug_g, rec_g = _DSUB_STEEL_G[int(shell_no)]
    grams = rec_g if gender == "Receptacle" else plug_g
    std = _DSUB_STD_PINS[int(shell_no)]
    extra = max(int(pin_count) - std, 0)
    grams += extra * 0.12
    if finish == "A":
        grams *= 0.58
    return grams / 453.59237


def compile_part_attributes(part_configuration):
    variant = variant_from_configuration(part_configuration)
    size = contact_size_for(variant.density)
    size_info = CONTACT_SIZES[size]

    contacts = [{"name": str(i), "size": size} for i in range(1, variant.pin_count + 1)]

    if variant.connector_type == "Crimp":
        tools = [
            f"{size_info['crimp_tool']} crimp tool",
            f"{size_info['extraction_tool']} extraction tool",
        ]
    else:
        tools = ["Soldering iron"]

    attributes = {
        "mass": f"{part_mass_lbs(variant.gender, variant.density, variant.shell_no, variant.pin_count, part_configuration['finish']):.4f}lbs",
        "mass_source": MASS_SOURCE,
        "tools": tools,
        "build_notes": [],
        "csys_children": {
            "3d-mate": mate_csys_3d(variant),
            **flagnote_csys_children(
                connector_depth_mm(variant) / MM_PER_IN,
                _mid(variant.dims["B"]) / 2.0,
            ),
        },
        "contacts": contacts,
    }
    return attributes


def iter_part_configurations():
    for variant in _VARIANTS:
        for finish in FINISHES:
            yield {
                "connector_type": variant.connector_type,
                "gender": variant.gender,
                "density": variant.density,
                "shell_no": variant.shell_no,
                "pin_count": variant.pin_count,
                "finish": finish,
            }


CATALOG_COLUMNS = (
    "library_pn",
    "official_pin",
    "mil_spec",
    "slash_sheet",
    "dash",
    "common_name",
    "gender",
    "contacts",
    "connector_type",
    "density",
    "shell_size",
    "shell_letter",
    "pin_count",
    "contact_size",
    "finish",
    "finish_name",
    "class",
)


def catalog_row(part_configuration):
    slash = slash_sheet(
        part_configuration["connector_type"], part_configuration["gender"]
    )
    dash = dash_number(
        part_configuration["density"], part_configuration["shell_no"]
    )
    letter = SHELL_LETTERS.get(part_configuration["shell_no"], "")
    gender = part_configuration["gender"]
    return {
        "library_pn": make_part_number(part_configuration),
        "official_pin": official_pin(part_configuration),
        "mil_spec": "MIL-DTL-24308",
        "slash_sheet": slash,
        "dash": dash,
        "common_name": common_name(part_configuration),
        "gender": gender,
        "contacts": "socket" if gender == "Receptacle" else "pin",
        "connector_type": part_configuration["connector_type"],
        "density": part_configuration["density"],
        "shell_size": part_configuration["shell_no"],
        "shell_letter": letter,
        "pin_count": part_configuration["pin_count"],
        "contact_size": contact_size_for(part_configuration["density"]),
        "finish": part_configuration["finish"],
        "finish_name": FINISHES[part_configuration["finish"]],
        "class": "G",
    }


def write_catalog_csv(path=None):
    """Write dsub/dsub.csv — one row per library part."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dsub.csv")
    rows = [catalog_row(cfg) for cfg in iter_part_configurations()]
    rows.sort(key=lambda r: (int(r["slash_sheet"]), int(r["dash"]), r["finish"]))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=CATALOG_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _progress_bar(done, total, width=25):
    """Return a text progress bar like: [ x x x . . . ] (35%)."""
    if total <= 0:
        filled = width
        pct = 100
    else:
        filled = min(width, max(0, round(width * done / total)))
        pct = round(100.0 * done / total)
    cells = ["x"] * filled + ["."] * (width - filled)
    return "[ " + " ".join(cells) + f" ] ({pct}%)"


def make_part(part_configuration):
    """Write one D-sub part folder, attributes, SVG, and run harnice -b."""
    part_number = make_part_number(part_configuration)
    print("Preparing part number: ", part_number)

    family_dir = os.path.dirname(os.path.abspath(__file__))
    part_dir = os.path.join(family_dir, part_number)
    os.makedirs(part_dir, exist_ok=True)

    revision_history_content_dict = {
        "project_type": state.project_type,
        "mfg": "mil spec",
        "pn": part_number,
        "rev": REVISION,
        "desc": "",
        "status": "",
        "datestarted": DATE_STARTED,
        "library_repo": "https://github.com/harnice/harnice-aerospace-library",
        "library_subpath": "dsub",
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
    attributes = compile_part_attributes(part_configuration)
    with open(json_path, "w") as f:
        json.dump(attributes, f, indent=2)

    variant = variant_from_configuration(part_configuration)
    svg_content = dsub_connector_svg(part_number, variant)
    svg_path = os.path.join(rev_dir, f"{part_number}-rev{REVISION}-drawing.svg")
    with open(svg_path, "w") as f:
        f.write(svg_content)

    write_part_step(rev_dir, part_number, variant)

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
        print(f"{total} legal D-sub configurations in the permutation space.")
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
            variant = variant_from_configuration(part_configuration)
            json_path = os.path.join(
                rev_dir, f"{part_number}-rev{REVISION}-attributes.json"
            )
            with open(json_path, "w") as f:
                json.dump(compile_part_attributes(part_configuration), f, indent=2)
            svg_path = os.path.join(
                rev_dir, f"{part_number}-rev{REVISION}-drawing.svg"
            )
            with open(svg_path, "w") as f:
                f.write(dsub_connector_svg(part_number, variant))
            write_part_step(rev_dir, part_number, variant)
            print(_progress_bar(i, total))
            continue
        make_part(part_configuration)
        print(_progress_bar(i, total))

    print("Finished rendering all parts in family.")


if __name__ == "__main__":
    main()
