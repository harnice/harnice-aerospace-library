import csv
import json
import math
import os
import subprocess
import sys

from harnice import fileio, state
from harnice.lists import rev_history
from harnice.project_types import cable

REVISION = "1"
DATE_STARTED = "8/17/26"

# ---------------------------------------------------------------------------
# Datasheet / specification sources (traceability)
# ---------------------------------------------------------------------------
# Part number anatomy, Table I (basic wire specifications), Table I A (shield
# style and material), Table I B (jacket material and color), Table II
# (allowable shield and jacket materials per basic wire type), and
# Tables III A / III B / III C (circuit identification colors):
#   MIL-DTL-27500 / NEMA WC 27500 cable designations, as reproduced by
#   Standard Wire & Cable Co.
#   https://standard-wire.com/resource/mil-dtl-27500-nema-wc27500-cable-designations/
#
# Component wire dimensions (stranding, conductor dia, finished wire dia,
# resistance, temperature and voltage rating) per slash sheet:
#   M22759/11, /16, /18, /32, /33 — Glenair M22759 Wires catalog
#   https://www.glenair.com/wire-and-cable/m22759-wires/pdf/m22759-wires.pdf
#   M22759/16 and /18 corroboration — SAE AS22759/16 and /18 datasheet
#   https://cdn-e.soneparcanada.io/PIM_Docs/Docs/STEP_ASSETS_PDF/566778039.pdf
#   M81044/9, /12 — Ryan Electronics M81044 slash sheet tables
#   https://www.ryanelectronics.com/products/m810449/
#   https://www.ryanelectronics.com/products/m8104412/
#   M81381/13 — FDH Aero / Thermax MIL-DTL-81381 catalog
#   https://fdhaero.com/item/m81381-13-wire-medium-weight-high-strength-conductor/
#
# Component-wire mass (`weight_lb_per_kft`) is the slash-sheet maximum
# lbs/1000 ft:
#   M22759/11 — Ryan Electronics / Glenair
#   https://www.ryanelectronics.com/products/m2275911/
#   M22759/16 — Glenair
#   https://cdn.glenair.com/wire-and-cable/pdf/b/m22759-16.pdf
#   M22759/18 — Glenair M22759 wires catalog
#   https://www.glenair.com/wire-and-cable/m22759-wires/pdf/m22759-wires.pdf
#   M22759/32 and /33 — Glenair wire-diameter lookup tables
#   https://www.glenair.com/guardian-conduit-system/pdf/wire-diameter-lookup-tables.pdf
#   M81044/9, /12 — Ryan Electronics
#   https://www.ryanelectronics.com/products/m810449/
#   https://www.ryanelectronics.com/products/m8104412/
#   M81381/13 — FDH Aero / Thermax
#   https://fdhaero.com/item/m81381-13-wire-medium-weight-high-strength-conductor/
#
# MIL-DTL-27500 does NOT tabulate finished cable outside diameter or finished
# cable weight; those are a function of the component wire OD, conductor
# count, shield braid and jacket wall. Component wire ODs and lbs/1000 ft
# below are datasheet values. The cable buildup (core packing, braid wall,
# jacket wall) is a geometric estimate — see "Cable diameter buildup model"
# and treat overall OD and shield/jacket mass as low-fidelity.
# ---------------------------------------------------------------------------


# ===========================================================================
# Table I — Basic wire specifications (curated subset)
# ===========================================================================
# Only the symbols this generator has cited dimensional data for. `slash`
# drives the Table II shield/jacket lookup. `wire_od_in` is the datasheet
# nominal finished wire diameter, keyed by AWG; a gauge is only buildable if
# it appears here. `resistance_ohm_per_kft` is the datasheet maximum at 20 C.
BASIC_WIRE_SPECS = {
    "RC": {
        "spec": "MIL-DTL-22759/11",
        "slash": 11,
        "insulation": "PTFE",
        "conductor_material": "silver-coated copper",
        "temperature_c": 200,
        "voltage_v": 600,
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
        "weight_source": (
            "M22759/11 slash-sheet max weight, lbs/1000 ft "
            "(Glenair M22759 wires / Ryan Electronics, "
            "https://www.ryanelectronics.com/products/m2275911/)"
        ),
    },
    "TE": {
        "spec": "MIL-DTL-22759/16",
        "slash": 16,
        "insulation": "ETFE, extruded, medium wall",
        "conductor_material": "tin-coated copper",
        "temperature_c": 150,
        "voltage_v": 600,
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
        "weight_source": (
            "M22759/16 slash-sheet max weight, lbs/1000 ft "
            "(Glenair, https://cdn.glenair.com/wire-and-cable/pdf/b/m22759-16.pdf)"
        ),
    },
    "TG": {
        "spec": "MIL-DTL-22759/18",
        "slash": 18,
        "insulation": "ETFE, extruded, thin wall",
        "conductor_material": "tin-coated copper",
        "temperature_c": 150,
        "voltage_v": 600,
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
        "weight_source": (
            "M22759/18 slash-sheet max weight, lbs/1000 ft "
            "(Glenair M22759 wires catalog, "
            "https://www.glenair.com/wire-and-cable/m22759-wires/pdf/m22759-wires.pdf)"
        ),
    },
    "SB": {
        "spec": "MIL-DTL-22759/32",
        "slash": 32,
        "insulation": "crosslinked modified ETFE",
        "conductor_material": "tin-coated copper",
        "temperature_c": 150,
        "voltage_v": 600,
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
        "weight_source": (
            "M22759/32 slash-sheet max weight, lbs/1000 ft "
            "(Glenair wire diameter lookup tables, "
            "https://www.glenair.com/guardian-conduit-system/pdf/wire-diameter-lookup-tables.pdf)"
        ),
    },
    "SC": {
        "spec": "MIL-DTL-22759/33",
        "slash": 33,
        "insulation": "crosslinked modified ETFE",
        "conductor_material": "silver-coated high-strength copper alloy",
        "temperature_c": 200,
        "voltage_v": 600,
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
        "weight_source": (
            "M22759/33 slash-sheet weight, lbs/1000 ft, from Glenair "
            "M27500-xxSC2U00 pairs in "
            "https://www.glenair.com/guardian-conduit-system/pdf/wire-diameter-lookup-tables.pdf"
        ),
    },
    "MH": {
        "spec": "MIL-DTL-81044/9",
        "slash": 9,
        "insulation": "crosslinked polyalkene with crosslinked PVDF jacket",
        "conductor_material": "tin-coated copper",
        "temperature_c": 150,
        "voltage_v": 600,
        "wire_od_in": {
            24: 0.054,
            22: 0.062,
            20: 0.070,
            18: 0.080,
            16: 0.089,
            14: 0.108,
            12: 0.126,
            10: 0.155,
            8: 0.214,
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
            24: 3.20,
            22: 4.50,
            20: 6.50,
            18: 9.55,
            16: 12.1,
            14: 18.4,
            12: 27.8,
            10: 43.0,
            8: 76.5,
        },
        "weight_source": (
            "M81044/9 slash-sheet max weight, lbs/1000 ft "
            "(Ryan Electronics, https://www.ryanelectronics.com/products/m810449/)"
        ),
    },
    "ML": {
        "spec": "MIL-DTL-81044/12",
        "slash": 12,
        "insulation": "crosslinked polyalkene with crosslinked PVDF jacket, light wall",
        "conductor_material": "tin-coated copper",
        "temperature_c": 150,
        "voltage_v": 600,
        "wire_od_in": {
            30: 0.027,
            28: 0.030,
            26: 0.034,
            24: 0.040,
            22: 0.047,
            20: 0.055,
            18: 0.065,
            16: 0.072,
            14: 0.089,
            12: 0.108,
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
            30: 0.81,
            28: 1.10,
            26: 1.58,
            24: 2.25,
            22: 3.19,
            20: 4.82,
            18: 7.25,
            16: 9.15,
            14: 14.2,
            12: 21.7,
        },
        "weight_source": (
            "M81044/12 slash-sheet max weight, lbs/1000 ft "
            "(Ryan Electronics, https://www.ryanelectronics.com/products/m8104412/)"
        ),
    },
    "NA": {
        "spec": "MIL-DTL-81381/13",
        "slash": 13,
        "insulation": "FEP/polyimide/FEP tape with aromatic polyimide coating",
        "conductor_material": "silver-coated high-strength copper alloy",
        "temperature_c": 200,
        "voltage_v": 600,
        # Datasheet lists min/max insulation dia; nominal is the midpoint.
        "wire_od_in": {
            28: 0.033,
            26: 0.038,
            24: 0.043,
            22: 0.049,
            20: 0.057,
        },
        "resistance_ohm_per_kft": {
            28: 74.4,
            26: 44.8,
            24: 28.4,
            22: 17.5,
            20: 10.7,
        },
        "weight_lb_per_kft": {
            28: 1.10,
            26: 1.54,
            24: 2.15,
            22: 3.10,
            20: 4.65,
        },
        "weight_source": (
            "M81381/13 slash-sheet max weight, lbs/1000 ft "
            "(FDH Aero / Thermax, "
            "https://fdhaero.com/item/m81381-13-wire-medium-weight-high-strength-conductor/)"
        ),
    },
}

# Standard MIL stranding by conductor size (number of strands x strand AWG).
# Shared by every slash sheet above at a given gauge.
#
# NOTE: the Glenair M22759 catalog prints "19 x 25" for 12 AWG on /11, /16 and
# /18. The SAE AS22759/16 and /18 sheet and the Amphenol catalog both give
# 37 x 28, which is the standard MIL stranding, so 37/28 is used here.
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
# M81381/13 in 28 AWG is 7/36, matching STRANDING; no per-spec override needed.


# ===========================================================================
# Table I A — Shield style and material
# ===========================================================================
# "double" pairs each single-shield letter with its double-shield letter. A
# double shield implies a jacket between the two shields, so double shield
# codes are only legal against double jacket codes (Table I B 51-74).
SHIELD_CODES = {
    "U": {"description": "no shield", "material": None, "style": None, "temperature_c": None, "double": None, "density_lb_in3": 0.0},
    "T": {"description": "round, tin-coated copper", "material": "tin-coated copper", "style": "round braid", "temperature_c": 150, "double": "V", "density_lb_in3": 0.321},
    "S": {"description": "round, silver-coated copper", "material": "silver-coated copper", "style": "round braid", "temperature_c": 200, "double": "W", "density_lb_in3": 0.321},
    "N": {"description": "round, nickel-coated copper", "material": "nickel-coated copper", "style": "round braid", "temperature_c": 260, "double": "Y", "density_lb_in3": 0.321},
    "F": {"description": "round, stainless steel", "material": "stainless steel", "style": "round braid", "temperature_c": 400, "double": "Z", "density_lb_in3": 0.284},
    "C": {"description": "round, heavy nickel-coated copper", "material": "heavy nickel-coated copper", "style": "round braid", "temperature_c": 400, "double": "R", "density_lb_in3": 0.321},
    "M": {"description": "round, silver-coated high strength copper alloy", "material": "silver-coated high-strength copper alloy", "style": "round braid", "temperature_c": 200, "double": "K", "density_lb_in3": 0.321},
    "P": {"description": "round, nickel-coated high strength copper alloy", "material": "nickel-coated high-strength copper alloy", "style": "round braid", "temperature_c": 260, "double": "L", "density_lb_in3": 0.321},
    "G": {"description": "flat, silver-coated copper", "material": "silver-coated copper", "style": "flat braid", "temperature_c": 200, "double": "A", "density_lb_in3": 0.321},
    "H": {"description": "flat, silver-coated high strength copper alloy", "material": "silver-coated high-strength copper alloy", "style": "flat braid", "temperature_c": 200, "double": "B", "density_lb_in3": 0.321},
    "J": {"description": "flat, tin-coated copper", "material": "tin-coated copper", "style": "flat braid", "temperature_c": 150, "double": "D", "density_lb_in3": 0.321},
    "E": {"description": "flat, nickel-coated high strength copper alloy", "material": "nickel-coated high-strength copper alloy", "style": "flat braid", "temperature_c": 260, "double": "X", "density_lb_in3": 0.321},
    "I": {"description": "flat, nickel-chromium alloy", "material": "nickel-chromium alloy", "style": "flat braid", "temperature_c": 400, "double": "Q", "density_lb_in3": 0.284},
}
# Table I A also lists "*" (single) / "#" (double) for flat nickel-coated
# copper. Those characters are omitted here because they are not safe in a
# part number used as a directory name.

DOUBLE_SHIELD_CODES = {
    info["double"]: {**info, "shields": 2, "single_code": code}
    for code, info in SHIELD_CODES.items()
    if info["double"]
}


# ===========================================================================
# Table I B — Jacket material and color
# ===========================================================================
# `construction` drives the jacket wall estimate in the diameter buildup.
# `double` is the equivalent double-jacket numeric code.
# `density_lb_in3` is a typical polymer density used only for the geometric
# shield/jacket mass adder; MIL-DTL-27500 does not tabulate jacket mass.
JACKET_CODES = {
    "00": {"description": "no jacket", "material": None, "color": None, "construction": None, "temperature_c": None, "double": "00", "density_lb_in3": 0.0},
    "01": {"description": "extruded white polyvinylchloride (PVC)", "material": "PVC", "color": "white", "construction": "extruded", "temperature_c": 90, "double": "51", "density_lb_in3": 0.051},
    "02": {"description": "extruded clear polyamide", "material": "polyamide", "color": "clear", "construction": "extruded", "temperature_c": 105, "double": "52", "density_lb_in3": 0.041},
    "03": {"description": "white polyamide braid impregnated with clear polyamide finisher over polyester tape", "material": "polyamide", "color": "white", "construction": "braid", "temperature_c": 105, "double": "53", "density_lb_in3": 0.041},
    "04": {"description": "polyester braid impregnated with high temperature finishers over polyester tape", "material": "polyester", "color": "natural", "construction": "braid", "temperature_c": 150, "double": "54", "density_lb_in3": 0.05},
    "05": {"description": "extruded clear fluorinated ethylene propylene (FEP)", "material": "FEP", "color": "clear", "construction": "extruded", "temperature_c": 200, "double": "55", "density_lb_in3": 0.078},
    "06": {"description": "extruded or taped and heat sealed white polytetrafluoroethylene (PTFE)", "material": "PTFE", "color": "white", "construction": "extruded", "temperature_c": 260, "double": "56", "density_lb_in3": 0.078},
    "07": {"description": "white PTFE treated glass braid over presintered PTFE tape", "material": "PTFE-coated glass", "color": "white", "construction": "braid", "temperature_c": 260, "double": "57", "density_lb_in3": 0.072},
    "08": {"description": "crosslinked white extruded polyvinylidene fluoride (PVDF)", "material": "PVDF", "color": "white", "construction": "extruded", "temperature_c": 150, "double": "58", "density_lb_in3": 0.064},
    "09": {"description": "extruded white fluorinated ethylene propylene (FEP)", "material": "FEP", "color": "white", "construction": "extruded", "temperature_c": 200, "double": "59", "density_lb_in3": 0.078},
    "10": {"description": "extruded clear polyvinylidene fluoride (PVDF)", "material": "PVDF", "color": "clear", "construction": "extruded", "temperature_c": 125, "double": "60", "density_lb_in3": 0.064},
    "11": {"description": "natural polyimide/FEP tape, heat sealed, FEP outer surface", "material": "polyimide/FEP tape", "color": "natural", "construction": "tape", "temperature_c": 200, "double": "61", "density_lb_in3": 0.051},
    "12": {"description": "natural polyimide/FEP tape, heat sealed, polyimide outer surface", "material": "polyimide/FEP tape", "color": "natural", "construction": "tape", "temperature_c": 200, "double": "62", "density_lb_in3": 0.051},
    "14": {"description": "extruded white ethylene-tetrafluoroethylene copolymer (ETFE)", "material": "ETFE", "color": "white", "construction": "extruded", "temperature_c": 150, "double": "64", "density_lb_in3": 0.061},
    "15": {"description": "extruded clear ethylene-tetrafluoroethylene copolymer (ETFE)", "material": "ETFE", "color": "clear", "construction": "extruded", "temperature_c": 150, "double": "65", "density_lb_in3": 0.061},
    "16": {"description": "aromatic polyamide braid with high temperature finisher over presintered PTFE tape", "material": "aromatic polyamide", "color": "natural", "construction": "braid", "temperature_c": 200, "double": "66", "density_lb_in3": 0.044},
    "17": {"description": "extruded white ethylene chlorotrifluoroethylene (ECTFE)", "material": "ECTFE", "color": "white", "construction": "extruded", "temperature_c": 150, "double": "67", "density_lb_in3": 0.061},
    "18": {"description": "extruded clear ethylene chlorotrifluoroethylene (ECTFE)", "material": "ECTFE", "color": "clear", "construction": "extruded", "temperature_c": 150, "double": "68", "density_lb_in3": 0.061},
    "20": {"description": "extruded white perfluoroalkoxy (PFA)", "material": "PFA", "color": "white", "construction": "extruded", "temperature_c": 260, "double": "70", "density_lb_in3": 0.078},
    "21": {"description": "extruded clear perfluoroalkoxy (PFA)", "material": "PFA", "color": "clear", "construction": "extruded", "temperature_c": 260, "double": "71", "density_lb_in3": 0.078},
    "22": {"description": "polyimide/clear FEP tape, heat sealed, opaque polyimide outer surface", "material": "polyimide/FEP tape", "color": "opaque", "construction": "tape", "temperature_c": 200, "double": "72", "density_lb_in3": 0.051},
    "23": {"description": "extruded white crosslinked modified ETFE (XLETFE)", "material": "XLETFE", "color": "white", "construction": "extruded", "temperature_c": 200, "double": "73", "density_lb_in3": 0.061},
    "24": {"description": "white PTFE tape over natural polyimide/FEP tape, heat sealed", "material": "PTFE over polyimide/FEP tape", "color": "white", "construction": "tape", "temperature_c": 200, "double": "74", "density_lb_in3": 0.07},
}

DOUBLE_JACKET_CODES = {
    info["double"]: {**info, "jackets": 2, "single_code": code}
    for code, info in JACKET_CODES.items()
    if info["double"] and info["double"] != code
}


# ===========================================================================
# Table II — Allowable shield and jacket materials for each basic wire type
# ===========================================================================
# Keyed by (base specification, slash-sheet predicate). `shields` are the
# legal single-shield letters; `jackets` are the legal single-jacket codes for
# the jacketed and shielded-and-jacketed cable types. A shielded unjacketed
# cable always carries jacket code 00.
TABLE_II = [
    {
        "spec": "MIL-DTL-5086",
        "slashes": range(1, 8),
        "shields": ["T"],
        "jackets": ["01", "02", "03", "10"],
    },
    {
        "spec": "MIL-DTL-8777",
        "slashes": None,
        "shields": ["S"],
        "jackets": ["04"],
    },
    {
        "spec": "MIL-DTL-22759",
        "slashes": list(range(1, 13)) + list(range(20, 24)) + list(range(28, 32)),
        "shields": ["T", "S", "N"],
        "jackets": ["04", "05", "06", "07", "09", "14", "15", "16", "17", "18", "20", "21"],
    },
    {
        "spec": "MIL-DTL-22759",
        "slashes": range(13, 20),
        "shields": ["T", "S", "N"],
        "jackets": ["04", "05", "09", "14", "15", "16", "17", "18", "20", "21"],
    },
    {
        "spec": "MIL-DTL-22759",
        "slashes": list(range(32, 36)) + list(range(41, 47)),
        "shields": ["T", "S", "N"],
        "jackets": ["04", "05", "08", "09", "14", "15", "16", "17", "18", "20", "21", "23", "24"],
    },
    {
        "spec": "MIL-DTL-22759",
        "slashes": range(80, 93),
        "shields": ["T", "S", "N"],
        "jackets": ["04", "05", "06", "07", "09", "11", "12", "14", "15", "16", "17", "18", "20", "21", "22", "24"],
    },
    {
        "spec": "MIL-DTL-25038",
        "slashes": [1, 3],
        "shields": ["F", "C"],
        "jackets": ["06", "07"],
    },
    {
        "spec": "MIL-DTL-81044",
        "slashes": None,
        "shields": ["T", "S"],
        "jackets": ["04", "08", "09", "14", "16", "23"],
    },
    {
        "spec": "MIL-DTL-81381",
        "slashes": None,
        "shields": ["T", "S", "N"],
        "jackets": ["05", "09", "11", "12", "22"],
    },
]


def table_ii_row(symbol):
    """Return the Table II row governing a Table I basic wire symbol."""
    spec = BASIC_WIRE_SPECS[symbol]
    base = spec["spec"].split("/")[0]
    slash = spec["slash"]
    for row in TABLE_II:
        if row["spec"] != base:
            continue
        if row["slashes"] is None or slash in row["slashes"]:
            return row
    raise ValueError(
        f"No MIL-DTL-27500 Table II row covers {spec['spec']} (symbol '{symbol}')"
    )


# ===========================================================================
# Identification method (part number position 2) and shield coverage
# ===========================================================================
# "-" and "F" are the preferred method (white wire with colored stripes);
# "A"/"G" are optional method A (solid colored wires). Optional methods B, C
# and D (band and print marking) need Tables III D / III E, which are not
# transcribed here, so those codes are declared but not buildable.
IDENTIFICATION_METHODS = {
    "-": {"coverage": "85%", "color_table": "IIIA", "marking": "stripe"},
    "F": {"coverage": "85%", "color_table": "IIIB", "marking": "stripe"},
    "A": {"coverage": "85%", "color_table": "IIIA", "marking": "solid"},
    "G": {"coverage": "85%", "color_table": "IIIB", "marking": "solid"},
    "B": {"coverage": "85%", "color_table": "IIIC", "marking": "band"},
    "K": {"coverage": "85%", "color_table": None, "marking": "print"},
    "L": {"coverage": "85%", "color_table": None, "marking": "print"},
    "C": {"coverage": "90%", "color_table": "IIIA", "marking": "stripe"},
    "H": {"coverage": "90%", "color_table": "IIIB", "marking": "stripe"},
    "D": {"coverage": "90%", "color_table": "IIIA", "marking": "solid"},
    "J": {"coverage": "90%", "color_table": "IIIB", "marking": "solid"},
    "E": {"coverage": "90%", "color_table": "IIIC", "marking": "band"},
    "M": {"coverage": "90%", "color_table": None, "marking": "print"},
    "N": {"coverage": "90%", "color_table": None, "marking": "print"},
}

SUPPORTED_MARKINGS = ("stripe", "solid")


# ===========================================================================
# Tables III A / III B / III C — Circuit identification colors
# ===========================================================================
# Table III A: circuit identification colors by wire number, for basic wires
# per MIL-DTL-22759, /25038, /81044 or /81381. Wires 11-15 use a white base
# with a double color tracer, expressed here as a repeated color.
TABLE_IIIA = [
    ["white"],
    ["blue"],
    ["orange"],
    ["green"],
    ["red"],
    ["black"],
    ["yellow"],
    ["violet"],
    ["gray"],
    ["brown"],
    ["blue", "blue"],
    ["orange", "orange"],
    ["green", "green"],
    ["red", "red"],
    ["black", "black"],
]

# Table III B: alternate sequence, also legal for MIL-DTL-50861 and /8777
# basic wire. "basic" is the basic wire color (white). Wires 11-15 are a
# solid color with a white stripe.
TABLE_IIIB = [
    ["red"],
    ["blue"],
    ["yellow"],
    ["green"],
    ["white"],
    ["black"],
    ["brown"],
    ["orange"],
    ["violet"],
    ["gray"],
    ["red", "white"],
    ["blue", "white"],
    ["yellow", "white"],
    ["green", "white"],
    ["black", "white"],
]

# Table III C: insulation color identifying wire size per MIL-STD-686. Used
# by optional identification method B, where every wire in the cable shares
# this color and contrasting bands denote the wire number.
TABLE_IIIC = {
    26: "black",
    24: "blue",
    22: "green",
    20: "red",
    18: "white",
    16: "blue",
    14: "green",
    12: "yellow",
    10: "brown",
    8: "red",
    6: "blue",
    4: "yellow",
    2: "red",
}


def identification_colors(color_table, n_conductors, gauge):
    """Return the per-wire color lists for an identification color table."""
    if color_table == "IIIA":
        table = TABLE_IIIA
    elif color_table == "IIIB":
        table = TABLE_IIIB
    elif color_table == "IIIC":
        return [[TABLE_IIIC[gauge]] for _ in range(n_conductors)]
    else:
        raise ValueError(f"Unknown identification color table '{color_table}'")

    if n_conductors > len(table):
        raise ValueError(
            f"MIL-DTL-27500 Table {color_table} covers at most {len(table)} wires"
        )
    return table[:n_conductors]


def conductor_color_name(colors):
    """Return a wire's identifying color designation, per MIL-DTL-27500 Table III.

    This is the conductor's identifier. MIL-DTL-27500 numbers the wires in the
    cable, but a harnice cable identifies each conductor by its color (see the
    conductor keys in harnice.project_types.cable), and the color is what the
    technician looking at a stripped cable end actually sees. The wire number is
    kept as a property so the Table III ordering is not lost.

    The name is the Table III color itself, independent of how it is marked: the
    stripe method puts that color on a white wire and the solid method colors the
    insulation, but either way wire 2 of Table IIIA is identified as "blue". The
    white base of a striped wire is left out of the name because every striped
    wire in the cable shares it; the appearance still carries it. No Table III
    sequence repeats a designation this way, so identifiers stay unique out to
    the 15 wire depth of Tables IIIA and IIIB, including the Table IIIB cable
    that holds "red", "white" and "red/white" at once.
    """
    return "/".join(colors)


def conductor_appearance(colors, marking):
    """Build a harnice engineering appearance dict for one component wire.

    `colors` is that wire's Table III entry. Under the preferred (stripe)
    method every wire is white with the Table III color applied as a helical
    stripe, and wire 1 is unstriped basic white. Under optional method A the
    Table III color is the insulation color itself.
    """
    if marking == "solid":
        base = colors[0]
        appearance = {"base_color": base}
        if len(colors) > 1:
            appearance["parallelstripe"] = list(colors[1:])
        if base == "white":
            appearance["outline_color"] = "black"
        return appearance

    if marking == "stripe":
        appearance = {"base_color": "white", "outline_color": "black"}
        if colors != ["white"]:
            appearance["parallelstripe"] = list(colors)
        return appearance

    raise ValueError(f"Unsupported identification marking '{marking}'")


# ===========================================================================
# Cable diameter buildup model
# ===========================================================================
# MIL-DTL-27500 does not tabulate finished cable OD, so it is estimated from
# the datasheet component wire OD outward. Every number in this section is a
# geometric estimate, not a specification value.
#
# Core: ratio of the smallest enclosing circle to the component wire diameter
# for n equal circles packed in a circle (the classic "circles in a circle"
# constants).
CIRCLE_PACKING_RATIO = {
    1: 1.0000,
    2: 2.0000,
    3: 2.1547,
    4: 2.4142,
    5: 2.7013,
    6: 3.0000,
    7: 3.0000,
    8: 3.3048,
    9: 3.6131,
    10: 3.8130,
    11: 3.9238,
    12: 4.0296,
    13: 4.2361,
    14: 4.3284,
    15: 4.5213,
}
# Spirally laid wires sweep a slightly larger envelope than a straight
# parallel bundle. Applied to multi-conductor cores only.
LAY_ALLOWANCE = 1.02

# Shield braid wall, by the diameter it is applied over. A braid wall is
# roughly two braid-wire diameters because carriers cross over and under.
BRAID_WIRE_DIA_IN = ((0.150, 0.0040), (0.400, 0.0050), (float("inf"), 0.0063))

# Jacket wall by construction and the diameter it is applied over.
EXTRUDED_JACKET_WALL_IN = ((0.150, 0.010), (0.400, 0.014), (float("inf"), 0.020))
TAPE_JACKET_WALL_IN = 0.006
BRAID_JACKET_WALL_IN = 0.012


def _lookup_by_diameter(table, diameter_in):
    for limit, value in table:
        if diameter_in <= limit:
            return value
    return table[-1][1]


def braid_wall_in(over_diameter_in):
    """Estimated shield braid wall thickness over a given diameter."""
    return 2.0 * _lookup_by_diameter(BRAID_WIRE_DIA_IN, over_diameter_in)


def jacket_wall_in(jacket, over_diameter_in):
    """Estimated jacket wall thickness over a given diameter."""
    construction = jacket["construction"]
    if construction == "tape":
        return TAPE_JACKET_WALL_IN
    if construction == "braid":
        return BRAID_JACKET_WALL_IN
    return _lookup_by_diameter(EXTRUDED_JACKET_WALL_IN, over_diameter_in)


def core_diameter_in(wire_od_in, n_conductors):
    """Estimated diameter of the spirally laid component wire bundle."""
    ratio = CIRCLE_PACKING_RATIO[n_conductors]
    core = wire_od_in * ratio
    if n_conductors > 1:
        core *= LAY_ALLOWANCE
    return core


def cable_layers(wire_od_in, n_conductors, shield_code, jacket_code):
    """Return the physical layers outside the core, innermost first.

    Each layer is a dict with `kind` ("shield" or "jacket"), its Table I A /
    Table I B record, the estimated wall, and the OD it produces. A double
    shield puts a jacket between the two shields and another over the outer
    shield, per the Table I B double-jacket note.
    """
    is_double_shield = shield_code in DOUBLE_SHIELD_CODES
    is_double_jacket = jacket_code in DOUBLE_JACKET_CODES
    shield = DOUBLE_SHIELD_CODES[shield_code] if is_double_shield else SHIELD_CODES[shield_code]
    jacket = DOUBLE_JACKET_CODES[jacket_code] if is_double_jacket else JACKET_CODES[jacket_code]

    # Innermost-first ordering of the stackup. is_legal_configuration
    # guarantees a double shield and a double jacket only ever appear together.
    if is_double_shield:
        sequence = ["shield", "jacket", "shield", "jacket"]
    else:
        sequence = []
        if shield_code != "U":
            sequence.append("shield")
        if jacket_code != "00":
            sequence.append("jacket")

    od = core_diameter_in(wire_od_in, n_conductors)
    layers = []
    shield_index = 0
    jacket_index = 0
    for kind in sequence:
        if kind == "shield":
            shield_index += 1
            wall = braid_wall_in(od)
            od = od + 2.0 * wall
            layers.append(
                {
                    "kind": "shield",
                    "index": shield_index,
                    "record": shield,
                    "wall_in": wall,
                    "od_in": od,
                }
            )
        else:
            jacket_index += 1
            wall = jacket_wall_in(jacket, od)
            od = od + 2.0 * wall
            layers.append(
                {
                    "kind": "jacket",
                    "index": jacket_index,
                    "record": jacket,
                    "wall_in": wall,
                    "od_in": od,
                }
            )
    return layers, od


def _annulus_lb_per_ft(od_in, wall_in, density, fill):
    inner = max(od_in - 2.0 * wall_in, 0.0)
    area = math.pi / 4.0 * (od_in ** 2 - inner ** 2)
    return area * 12.0 * density * fill


def component_wire_lb_per_ft(symbol, gauge):
    return BASIC_WIRE_SPECS[symbol]["weight_lb_per_kft"][int(gauge)] / 1000.0


# 85% coverage × braid packing. Stainless / nichrome use 0.284 lb/in^3;
# copper-family shields use 0.321. Jacket fill is 0.92 extruded / 0.70 tape or braid.
SHIELD_FILL = 0.62


def cable_mass_lb_per_ft(identification, gauge, symbol, n_conductors, shield_code, jacket_code):
    spec = BASIC_WIRE_SPECS[symbol]
    gauge = int(gauge)
    n_conductors = int(n_conductors)
    mass = n_conductors * component_wire_lb_per_ft(symbol, gauge)
    layers, _ = cable_layers(
        spec["wire_od_in"][gauge], n_conductors, shield_code, jacket_code
    )
    coverage = float(IDENTIFICATION_METHODS[identification]["coverage"].rstrip("%")) / 100.0
    for layer in layers:
        if layer["kind"] == "shield":
            density = layer["record"]["density_lb_in3"]
            fill = SHIELD_FILL * (coverage / 0.85)
        else:
            density = layer["record"]["density_lb_in3"]
            construction = layer["record"]["construction"]
            fill = 0.92 if construction == "extruded" else 0.70
        mass += _annulus_lb_per_ft(layer["od_in"], layer["wall_in"], density, fill)
    return mass


def cable_mass_source(symbol, shield_code, jacket_code):
    wire = BASIC_WIRE_SPECS[symbol]["weight_source"]
    if shield_code == "U" and jacket_code == "00":
        return wire
    return (
        f"Component wires: {wire}. Shield and jacket mass are a geometric "
        "estimate from the same core-packing / braid-wall / jacket-wall model "
        "used for OD; MIL-DTL-27500 does not tabulate finished cable weight."
    )


# ===========================================================================
# Part number composition and configuration legality
# ===========================================================================
def make_part_number(identification, gauge, symbol, n_conductors, shield_code, jacket_code):
    """Compose a MIL-DTL-27500 part number.

    e.g. M27500-22TG2T14: preferred identification, 22 AWG M22759/18
    component wires, 2 conductors, round tin-coated copper shield, extruded
    white ETFE jacket.
    """
    return (
        f"M27500{identification}{gauge}{symbol}{n_conductors}{shield_code}{jacket_code}"
    )


def is_legal_configuration(identification, gauge, symbol, n_conductors, shield_code, jacket_code):
    """Return (True, None) if the configuration is buildable, else (False, reason)."""
    method = IDENTIFICATION_METHODS.get(identification)
    if method is None:
        return False, f"unknown identification method '{identification}'"
    if method["marking"] not in SUPPORTED_MARKINGS:
        return False, (
            f"identification method '{identification}' uses "
            f"{method['marking']} marking, which needs Table III D/III E"
        )

    spec = BASIC_WIRE_SPECS.get(symbol)
    if spec is None:
        return False, f"unknown basic wire specification symbol '{symbol}'"
    if gauge not in spec["wire_od_in"]:
        return False, f"{spec['spec']} is not offered in {gauge} AWG"

    if not 1 <= n_conductors <= 15:
        return False, "MIL-DTL-27500 covers 1 to 15 conductors"
    # 1 to 15 conductors for shielded cables, 2 to 15 for unshielded.
    if shield_code == "U" and n_conductors < 2:
        return False, "an unshielded cable needs at least 2 conductors"
    # Cables with 10 to 15 conductors are limited to 12 AWG and smaller.
    if n_conductors >= 10 and gauge < 12:
        return False, f"{n_conductors} conductors is limited to 12 AWG and smaller"

    if n_conductors > len(TABLE_IIIA) and method["color_table"] == "IIIA":
        return False, "more conductors than Table III A covers"

    row = table_ii_row(symbol)
    is_double_shield = shield_code in DOUBLE_SHIELD_CODES
    is_double_jacket = jacket_code in DOUBLE_JACKET_CODES
    single_shield = DOUBLE_SHIELD_CODES[shield_code]["single_code"] if is_double_shield else shield_code
    single_jacket = DOUBLE_JACKET_CODES[jacket_code]["single_code"] if is_double_jacket else jacket_code

    if single_shield != "U" and single_shield not in row["shields"]:
        return False, (
            f"shield '{shield_code}' is not allowed on {spec['spec']} "
            f"(Table II allows {', '.join(row['shields'])})"
        )
    if single_jacket != "00" and single_jacket not in row["jackets"]:
        return False, (
            f"jacket '{jacket_code}' is not allowed on {spec['spec']} "
            f"(Table II allows {', '.join(row['jackets'])})"
        )

    # A double jacket exists to separate two shields, so it requires one.
    if is_double_jacket and not is_double_shield:
        return False, "a double jacket requires a double shield"
    # A double shield needs a jacket between the two braids.
    if is_double_shield and not is_double_jacket:
        return False, "a double shield requires a double jacket"

    return True, None


def overall_temperature_c(symbol, shield_code, jacket_code):
    """Lowest temperature rating in the stackup, per Tables I, I A and I B."""
    ratings = [BASIC_WIRE_SPECS[symbol]["temperature_c"]]
    shield = DOUBLE_SHIELD_CODES.get(shield_code) or SHIELD_CODES[shield_code]
    jacket = DOUBLE_JACKET_CODES.get(jacket_code) or JACKET_CODES[jacket_code]
    if shield["temperature_c"] is not None:
        ratings.append(shield["temperature_c"])
    if jacket["temperature_c"] is not None:
        ratings.append(jacket["temperature_c"])
    return min(ratings)


# ===========================================================================
# attributes.json construction
# ===========================================================================
# harnice.project_types.cable.build walks attributes.json for any dict with
# "conductor": true and records (container, identifier) from the two
# enclosing keys. Nesting the wires under a "conductors" group inside the
# shield/jacket stackup therefore yields container "conductors" and
# identifier "1".."15" for every configuration.
CONDUCTOR_GROUP_KEY = "conductors"


def compile_cable_attributes(configuration):
    identification = configuration["identification"]
    gauge = configuration["gauge"]
    symbol = configuration["basic_wire"]
    n_conductors = configuration["conductors"]
    shield_code = configuration["shield"]
    jacket_code = configuration["jacket"]

    spec = BASIC_WIRE_SPECS[symbol]
    method = IDENTIFICATION_METHODS[identification]
    wire_od = spec["wire_od_in"][gauge]

    layers, overall_od = cable_layers(wire_od, n_conductors, shield_code, jacket_code)
    core_od = core_diameter_in(wire_od, n_conductors)
    colors = identification_colors(method["color_table"], n_conductors, gauge)

    group = {
        "properties": {
            "lay": "spirally laid",
            "count": str(n_conductors),
            "od": f"{core_od:.3f}in",
            "identification method": (
                f"MIL-DTL-27500 Table {method['color_table']}, {method['marking']} marking"
            ),
        }
    }
    for wire_number, wire_colors in enumerate(colors, start=1):
        # The color is the conductor identifier, so it keys the conductor and
        # becomes the identifier column of the conductor list.
        color_name = conductor_color_name(wire_colors)
        if color_name in group:
            raise ValueError(
                f"MIL-DTL-27500 Table {method['color_table']} repeats the color "
                f"'{color_name}' within {n_conductors} conductors, so it cannot "
                "identify them uniquely"
            )
        group[color_name] = {
            "conductor": True,
            "properties": {
                "mass": f"{component_wire_lb_per_ft(symbol, gauge):.4f}lbs/ft",
                "mass_source": spec["weight_source"],
                "wire number": str(wire_number),
                "component_wire": f"{spec['spec'].replace('MIL-DTL-', 'M')}-{gauge}",
                "gauge": f"{gauge}AWG",
                "construction": STRANDING[gauge],
                "material": spec["conductor_material"],
                "insulation material": spec["insulation"],
                "od": f"{wire_od:.3f}in",
                "resistance": f"{spec['resistance_ohm_per_kft'][gauge]}ohm/1000ft",
                "temperature rating": f"{spec['temperature_c']}C",
                "voltage rating": f"{spec['voltage_v']}V",
            },
            "appearance": conductor_appearance(wire_colors, method["marking"]),
        }

    # Wrap the conductor group in the stackup, innermost layer first, so the
    # outermost layer ends up as the top-level key.
    node = {CONDUCTOR_GROUP_KEY: group}
    n_shield_layers = sum(1 for layer in layers if layer["kind"] == "shield")
    n_jacket_layers = sum(1 for layer in layers if layer["kind"] == "jacket")
    for layer in layers:
        record = layer["record"]
        if layer["kind"] == "shield":
            key = "shield" if n_shield_layers == 1 else f"shield_{layer['index']}"
            properties = {
                "type": record["style"],
                "material": record["material"],
                "coverage": method["coverage"],
                "od": f"{layer['od_in']:.3f}in",
                "thickness": f"{layer['wall_in']:.3f}in",
                "temperature rating": f"{record['temperature_c']}C",
            }
        else:
            key = "jacket" if n_jacket_layers == 1 else f"jacket_{layer['index']}"
            properties = {
                "material": record["material"],
                "color": record["color"],
                "construction": record["construction"],
                "od": f"{layer['od_in']:.3f}in",
                "thickness": f"{layer['wall_in']:.3f}in",
                "temperature rating": f"{record['temperature_c']}C",
            }
        node = {key: {"properties": properties, **node}}

    shield_record = DOUBLE_SHIELD_CODES.get(shield_code) or SHIELD_CODES[shield_code]
    jacket_record = DOUBLE_JACKET_CODES.get(jacket_code) or JACKET_CODES[jacket_code]

    properties = {
        "mass": f"{cable_mass_lb_per_ft(identification, gauge, symbol, n_conductors, shield_code, jacket_code):.4f}lbs/ft",
        "mass_source": cable_mass_source(symbol, shield_code, jacket_code),
        "od": f"{overall_od:.3f}in",
        "conductors": str(n_conductors),
        "component_wire_specification": spec["spec"],
        "shield": shield_record["description"],
        "jacket": jacket_record["description"],
        "temperature rating": f"{overall_temperature_c(symbol, shield_code, jacket_code)}C",
        "voltage rating": f"{spec['voltage_v']}V",
    }
    if shield_code != "U":
        properties["shield coverage"] = method["coverage"]

    attributes = {
        "specification": "MIL-DTL-27500",
        "properties": properties,
        "tools": cable_tools(shield_code, jacket_code),
    }
    attributes.update(node)
    return attributes


def cable_tools(shield_code, jacket_code):
    tools = ["Cable cutter", "Wire stripper"]
    if jacket_code != "00":
        tools.append("Jacket slitting tool")
    if shield_code != "U":
        tools.extend(["Shield comb / pick"])
    return tools


# ===========================================================================
# Permutation configuration
# ===========================================================================
# The full MIL-DTL-27500 design space is far larger than is useful to
# materialize, so this is the curated set that gets generated by default.
# Widen it here, or narrow a run with the --basic-wire / --gauge / --conductors
# command line filters.
PERMUTATIONS = {
    # Preferred identification method: white wires with colored stripes,
    # 85% minimum shield coverage.
    "identification": ["-"],
    "basic_wire": ["RC", "TE", "TG", "SB", "SC", "MH", "ML", "NA"],
    "gauge": [24, 22, 20, 18, 16, 14, 12],
    "conductors": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "shield": ["U", "T", "S", "N"],
    # Commonly stocked jackets plus 00 (unjacketed). Filtered against
    # Table II per basic wire specification.
    "jacket": ["00", "05", "09", "14", "20", "23"],
}


def iter_cable_configurations(permutations=None, filters=None):
    """Yield every legal configuration in the permutation space."""
    permutations = permutations or PERMUTATIONS
    filters = filters or {}
    for identification in permutations["identification"]:
        for symbol in permutations["basic_wire"]:
            if filters.get("basic_wire") and symbol not in filters["basic_wire"]:
                continue
            for gauge in permutations["gauge"]:
                if filters.get("gauge") and gauge not in filters["gauge"]:
                    continue
                for n_conductors in permutations["conductors"]:
                    if filters.get("conductors") and n_conductors not in filters["conductors"]:
                        continue
                    for shield_code in permutations["shield"]:
                        for jacket_code in permutations["jacket"]:
                            legal, _ = is_legal_configuration(
                                identification,
                                gauge,
                                symbol,
                                n_conductors,
                                shield_code,
                                jacket_code,
                            )
                            if not legal:
                                continue
                            yield {
                                "identification": identification,
                                "gauge": gauge,
                                "basic_wire": symbol,
                                "conductors": n_conductors,
                                "shield": shield_code,
                                "jacket": jacket_code,
                            }


def configuration_part_number(configuration):
    return make_part_number(
        configuration["identification"],
        configuration["gauge"],
        configuration["basic_wire"],
        configuration["conductors"],
        configuration["shield"],
        configuration["jacket"],
    )


# ===========================================================================
# Generation
# ===========================================================================
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


# ===========================================================================
# Family index CSV
# ===========================================================================
# One flat row per part number so the family is searchable in a spreadsheet.
# Dimensions are bare numbers rather than the unit-suffixed strings that go in
# attributes.json ("0.043in"), so that columns sort and filter numerically;
# the unit is carried in the column name instead. Column names ending in
# _estimated are from the diameter buildup model, not from a specification.
CSV_COLUMNS = [
    "part_number",
    "rev",
    "specification",
    "conductors",
    "gauge_awg",
    "stranding",
    "basic_wire_symbol",
    "component_wire_spec",
    "component_wire_pn",
    "insulation_material",
    "conductor_material",
    "conductor_od_in",
    "conductor_resistance_ohm_per_1000ft",
    "identification_method",
    "identification_color_table",
    "identification_marking",
    "wire_identification_colors",
    "shield_code",
    "shield_description",
    "shield_material",
    "shield_style",
    "shield_coverage",
    "shield_temperature_c",
    "jacket_code",
    "jacket_description",
    "jacket_material",
    "jacket_color",
    "jacket_construction",
    "jacket_temperature_c",
    "core_od_in_estimated",
    "overall_od_in_estimated",
    "temperature_rating_c",
    "voltage_rating_v",
    "path",
]


def csv_row(configuration):
    """Flatten one configuration into a family index row."""
    identification = configuration["identification"]
    gauge = configuration["gauge"]
    symbol = configuration["basic_wire"]
    n_conductors = configuration["conductors"]
    shield_code = configuration["shield"]
    jacket_code = configuration["jacket"]

    spec = BASIC_WIRE_SPECS[symbol]
    method = IDENTIFICATION_METHODS[identification]
    wire_od = spec["wire_od_in"][gauge]
    part_number = configuration_part_number(configuration)

    _, overall_od = cable_layers(wire_od, n_conductors, shield_code, jacket_code)
    # Band and print marking methods have no Table III color sequence.
    if method["marking"] in SUPPORTED_MARKINGS:
        colors = identification_colors(method["color_table"], n_conductors, gauge)
    else:
        colors = []

    shielded = shield_code != "U"
    jacketed = jacket_code != "00"
    shield_record = DOUBLE_SHIELD_CODES.get(shield_code) or SHIELD_CODES[shield_code]
    jacket_record = DOUBLE_JACKET_CODES.get(jacket_code) or JACKET_CODES[jacket_code]

    return {
        "part_number": part_number,
        "rev": REVISION,
        "specification": "MIL-DTL-27500",
        "conductors": n_conductors,
        "gauge_awg": gauge,
        "stranding": STRANDING[gauge],
        "basic_wire_symbol": symbol,
        "component_wire_spec": spec["spec"],
        "component_wire_pn": f"{spec['spec'].replace('MIL-DTL-', 'M')}-{gauge}",
        "insulation_material": spec["insulation"],
        "conductor_material": spec["conductor_material"],
        "conductor_od_in": f"{wire_od:.3f}",
        "conductor_resistance_ohm_per_1000ft": spec["resistance_ohm_per_kft"][gauge],
        "identification_method": identification,
        "identification_color_table": method["color_table"],
        "identification_marking": method["marking"],
        # The conductor identifiers, in wire-number order. Same strings that key
        # the conductors in attributes.json and fill the conductor list's
        # identifier column, so a color found here can be searched for there.
        "wire_identification_colors": "|".join(
            conductor_color_name(c) for c in colors
        ),
        "shield_code": shield_code,
        "shield_description": shield_record["description"],
        "shield_material": shield_record["material"] or "",
        "shield_style": shield_record["style"] or "",
        "shield_coverage": method["coverage"] if shielded else "",
        "shield_temperature_c": shield_record["temperature_c"] or "",
        "jacket_code": jacket_code,
        "jacket_description": jacket_record["description"],
        "jacket_material": jacket_record["material"] or "",
        "jacket_color": jacket_record["color"] or "",
        "jacket_construction": jacket_record["construction"] or "",
        "jacket_temperature_c": jacket_record["temperature_c"] or "",
        "core_od_in_estimated": f"{core_diameter_in(wire_od, n_conductors):.3f}",
        "overall_od_in_estimated": f"{overall_od:.3f}",
        "temperature_rating_c": overall_temperature_c(symbol, shield_code, jacket_code),
        "voltage_rating_v": spec["voltage_v"],
        "path": f"{part_number}/{part_number}-rev{REVISION}",
    }


def write_family_csv(configurations, family_dir):
    """Write M27500.csv: one row per part, sorted by part number."""
    path = os.path.join(family_dir, "M27500.csv")
    rows = sorted(
        (csv_row(configuration) for configuration in configurations),
        key=lambda row: row["part_number"],
    )
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {len(rows)} rows to:\n{path}\n")
    return path


def cache_run_constant_lookups():
    """Resolve the per-part lookups that cannot change during a run, once.

    `rev_history.part_family_append` calls `get_git_hash_of_harnice_src` (which
    shells out to `git rev-parse`) and re-reads `drawnby.json` for every part.
    Across a few thousand cables that is the single largest cost in this
    process, and neither value can change while the run is in flight.
    """
    git_hash = fileio.get_git_hash_of_harnice_src()
    drawnby = fileio.drawnby()
    fileio.get_git_hash_of_harnice_src = lambda: git_hash
    fileio.drawnby = lambda: drawnby


def build_cable(part_number, rev_dir):
    """Run the harnice cable build in this process.

    Equivalent to `harnice -b` in **rev_dir**, minus the checks the CLI performs
    that this generator has already satisfied: it wrote the revision history
    itself, so it does not need `verify_revision_structure` to discover the part
    number, re-derive the library identity, or refresh datemodified. Skipping
    the CLI avoids paying interpreter startup and a harnice import per part.
    """
    cwd = os.getcwd()
    os.chdir(rev_dir)
    try:
        state.set_pn(part_number)
        state.set_rev(REVISION)
        state.set_file_structure(cable.file_structure())
        cable.generate_structure()
        cable.build()
    finally:
        os.chdir(cwd)


def write_revision_history(part_dir, part_number):
    rev_history.part_family_append(
        {
            "project_type": state.project_type,
            "mfg": "mil spec",
            "pn": part_number,
            "rev": REVISION,
            "desc": "",
            "status": "",
            "datestarted": DATE_STARTED,
            "library_repo": "https://github.com/harnice/harnice-aerospace-library",
            "library_subpath": "M27500",
        },
        os.path.join(part_dir, f"{part_number}-revision_history.tsv"),
    )


def main(configurations=None, no_build=False, dry_run=False, use_cli=False, csv_only=False):
    state.set_rev(REVISION)
    state.set_project_type("cable")

    configurations = list(configurations if configurations is not None else iter_cable_configurations())
    total = len(configurations)

    if dry_run:
        print(f"{total} legal configurations in the permutation space.\n")
        sample = configurations[:: max(1, total // 20)][:20]
        for configuration in sample:
            print(f"  {configuration_part_number(configuration)}")
        if total > len(sample):
            print(f"  ... and {total - len(sample)} more")
        return

    family_dir = os.path.dirname(os.path.abspath(__file__))

    if csv_only:
        write_family_csv(list(iter_cable_configurations()), family_dir)
        return

    cache_run_constant_lookups()

    for i, configuration in enumerate(configurations, start=1):
        part_number = configuration_part_number(configuration)
        print("Preparing part number: ", part_number)

        part_dir = os.path.join(family_dir, part_number)
        os.makedirs(part_dir, exist_ok=True)
        rev_dir = os.path.join(part_dir, f"{part_number}-rev{REVISION}")

        write_revision_history(part_dir, part_number)

        if os.path.exists(rev_dir):
            for item in os.listdir(rev_dir):
                item_path = os.path.join(rev_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
        else:
            os.makedirs(rev_dir)

        attributes = compile_cable_attributes(configuration)
        json_path = os.path.join(rev_dir, f"{part_number}-rev{REVISION}-attributes.json")
        with open(json_path, "w") as f:
            json.dump(attributes, f, indent=2)

        if not no_build:
            # Either path reads the attributes.json above and writes
            # <pn>-rev<N>-conductor_list.tsv next to it.
            if use_cli:
                subprocess.run(["harnice", "-b"], cwd=rev_dir, check=True)
            else:
                build_cable(part_number, rev_dir)

        print(_progress_bar(i, total))

    print("Finished generating all cables in family.")

    # Always indexes the full permutation space rather than this run's
    # selection, so regenerating a subset does not truncate the index.
    write_family_csv(list(iter_cable_configurations()), family_dir)


if __name__ == "__main__":
    main()
