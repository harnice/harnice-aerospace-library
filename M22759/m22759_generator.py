"""
Emit MIL-DTL-22759 / SAE AS22759 hookup-wire SKUs as Harnice cable products.

The catalog, legality filter and part-number grammar live in M22759.py.
This file only writes folders. Do not import it from a harness.

    {PN}/
      {PN}-revision_history.tsv
      {PN}-rev1/
        {PN}-rev1-attributes.json
        {PN}-rev1-conductor_list.tsv
"""

import csv
import json
import os
import sys

from harnice import fileio, state
from harnice.lists import rev_history
from harnice.project_types import cable

_FAMILY_DIR = os.path.dirname(os.path.abspath(__file__))
if _FAMILY_DIR not in sys.path:
    sys.path.insert(0, _FAMILY_DIR)

import M22759  # noqa: E402


REVISION = "1"
DATE_STARTED = "8/22/26"
LIBRARY_REPO = "https://github.com/harnice/harnice-aerospace-library"
LIBRARY_SUBPATH = "M22759"
MANUFACTURER = "mil spec"


def compile_cable_attributes(cfg):
    """Single insulated conductor. There is no jacket on these slash sheets.

    /11, /16, /18, /32 and /33 are single-wall hookup wire: the insulation
    is a property of the conductor. /41 is dual-wall commercially, but the
    published tables give only the finished OD, so inventing a jacket
    envelope would be a guess. Identifier is the MIL-STD-681 color
    designation. Conductor `od` is that finished-wire diameter.
    """
    slash = cfg["slash"]
    gauge = cfg["gauge"]
    color_code = cfg["color"]
    spec = M22759.SLASH_SHEETS[slash]
    names = M22759.color_names(color_code)
    identifier = M22759.color_name(color_code)
    wire_od = spec["wire_od_in"][gauge]
    mass_lb_per_ft = spec["weight_lb_per_kft"][gauge] / 1000.0

    appearance = {"base_color": names[0]}
    if names[0] == "white":
        appearance["outline_color"] = "black"
    if len(names) > 1:
        appearance["parallelstripe"] = names[1:]

    attributes = {
        "specification": spec["spec"],
        "family": "M22759",
        "series": f"/{slash}",
        "mfg": MANUFACTURER,
        "datasheet": spec["datasheet"],
        "properties": {
            "mass": f"{mass_lb_per_ft:.4f}lbs/ft",
            "mass_source": spec["weight_source"],
            "od": f"{wire_od:.3f}in",
            "conductors": "1",
            "gauge": f"{gauge}AWG",
            "insulation": spec["insulation_detail"],
            "conductor material": spec["conductor_material"],
            "temperature rating": f"{spec['temperature_c']}C",
            "voltage rating": f"{spec['voltage_v']}V",
            "color code": color_code,
            "color": identifier,
        },
        "tools": _tools(spec),
        "build_notes": [],
        identifier: {
            "conductor": True,
            "properties": {
                "mass": f"{mass_lb_per_ft:.4f}lbs/ft",
                "mass_source": spec["weight_source"],
                "gauge": f"{gauge}AWG",
                "construction": M22759.STRANDING[gauge],
                "material": spec["conductor_material"],
                "insulation material": spec["insulation_detail"],
                "od": f"{wire_od:.3f}in",
                "resistance": f"{spec['resistance_ohm_per_kft'][gauge]}ohm/1000ft",
                "temperature rating": f"{spec['temperature_c']}C",
                "voltage rating": f"{spec['voltage_v']}V",
            },
            "appearance": appearance,
        },
    }
    return attributes


def _tools(spec):
    tools = ["Wire cutter", "Wire stripper"]
    if spec["insulation"] == "PTFE":
        tools.append("Thermal wire stripper")
    return tools


def revision_history_row(cfg):
    return {
        "project_type": "cable",
        "mfg": MANUFACTURER,
        "pn": M22759.make_part_number(cfg),
        "rev": REVISION,
        "desc": M22759.description_from_cfg(cfg),
        "status": "",
        "datestarted": DATE_STARTED,
        "library_repo": LIBRARY_REPO,
        "library_subpath": LIBRARY_SUBPATH,
    }


# ===========================================================================
# Family index CSV
# ===========================================================================
# Columns match the chooser fields (slash, gauge, color) plus the published
# dimensional columns those fields select. insulation_wall_in is derived
# from finished OD minus conductor OD; the unit is in the column name.
CSV_COLUMNS = [
    "part_number",
    "official_pin",
    "rev",
    "slash",
    "gauge_awg",
    "color_code",
    "color_name",
    "specification",
    "insulation",
    "insulation_detail",
    "wall",
    "plating",
    "conductor",
    "conductor_material",
    "stranding",
    "conductor_od_in",
    "wire_od_in",
    "insulation_wall_in",
    "weight_lb_per_kft",
    "resistance_ohm_per_kft",
    "temperature_c",
    "voltage_v",
    "m27500_symbol",
    "datasheet",
    "path",
]


def csv_row(cfg):
    slash = cfg["slash"]
    gauge = cfg["gauge"]
    color = cfg["color"]
    spec = M22759.SLASH_SHEETS[slash]
    pn = M22759.make_part_number(cfg)
    return {
        "part_number": pn,
        "official_pin": M22759.official_pin(cfg),
        "rev": REVISION,
        "slash": slash,
        "gauge_awg": gauge,
        "color_code": color,
        "color_name": M22759.color_name(color),
        "specification": spec["spec"],
        "insulation": spec["insulation"],
        "insulation_detail": spec["insulation_detail"],
        "wall": spec["wall"],
        "plating": spec["plating"],
        "conductor": spec["conductor"],
        "conductor_material": spec["conductor_material"],
        "stranding": M22759.STRANDING[gauge],
        "conductor_od_in": f"{M22759.conductor_od_in(gauge):.4f}",
        "wire_od_in": f"{spec['wire_od_in'][gauge]:.3f}",
        "insulation_wall_in": f"{M22759.insulation_wall_in(slash, gauge):.4f}",
        "weight_lb_per_kft": spec["weight_lb_per_kft"][gauge],
        "resistance_ohm_per_kft": spec["resistance_ohm_per_kft"][gauge],
        "temperature_c": spec["temperature_c"],
        "voltage_v": spec["voltage_v"],
        "m27500_symbol": M22759.m27500_symbol(slash) or "",
        "datasheet": spec["datasheet"],
        "path": f"{pn}/{pn}-rev{REVISION}",
    }


def write_family_csv(configurations, family_dir):
    path = os.path.join(family_dir, "M22759.csv")
    rows = sorted(
        (csv_row(cfg) for cfg in configurations),
        key=lambda row: row["part_number"],
    )
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {len(rows)} rows to:\n{path}\n")
    return path


def cache_run_constant_lookups():
    """Resolve the per-SKU lookups that cannot change during a run, once."""
    git_hash = fileio.get_git_hash_of_harnice_src()
    drawnby = fileio.drawnby()
    fileio.get_git_hash_of_harnice_src = lambda: git_hash
    fileio.drawnby = lambda: drawnby


def build_cable(part_number, rev_dir):
    """Run the Harnice cable build in this process (equivalent to `harnice -b`)."""
    cwd = os.getcwd()
    os.chdir(rev_dir)
    try:
        state.set_pn(part_number)
        state.set_rev(REVISION)
        state.set_project_type("cable")
        state.set_file_structure(cable.file_structure())
        cable.generate_structure()
        cable.build()
    finally:
        os.chdir(cwd)


def _progress_bar(done, total, width=25):
    if total <= 0:
        filled = width
        pct = 100
    else:
        filled = min(width, max(0, round(width * done / total)))
        pct = round(100.0 * done / total)
    cells = ["x"] * filled + ["."] * (width - filled)
    return "[ " + " ".join(cells) + f" ] ({pct}%)"


def main(
    configurations=None,
    no_build=False,
    dry_run=False,
    csv_only=False,
    build=True,
):
    state.set_rev(REVISION)
    state.set_project_type("cable")

    configurations = list(
        configurations if configurations is not None else M22759.iter_part_configurations()
    )
    total = len(configurations)

    if dry_run:
        print(f"{total} legal M22759 configurations in the permutation space.\n")
        sample = configurations[:: max(1, total // 10)][:10]
        for cfg in sample:
            print(f"  {M22759.make_part_number(cfg)}    {M22759.official_pin(cfg)}")
        if total > len(sample):
            print(f"  ... and {total - len(sample)} more")
        return

    family_dir = _FAMILY_DIR

    if csv_only:
        write_family_csv(list(M22759.iter_part_configurations()), family_dir)
        return

    if build and not no_build:
        cache_run_constant_lookups()

    for index, cfg in enumerate(configurations, start=1):
        part_number = M22759.make_part_number(cfg)
        print("Preparing part number: ", part_number)

        part_dir = os.path.join(family_dir, part_number)
        os.makedirs(part_dir, exist_ok=True)
        rev_dir = os.path.join(part_dir, f"{part_number}-rev{REVISION}")
        os.makedirs(rev_dir, exist_ok=True)

        rev_history.part_family_append(
            revision_history_row(cfg),
            os.path.join(part_dir, f"{part_number}-revision_history.tsv"),
        )

        attributes = compile_cable_attributes(cfg)
        json_path = os.path.join(
            rev_dir, f"{part_number}-rev{REVISION}-attributes.json"
        )
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(attributes, handle, indent=2)
            handle.write("\n")

        if build and not no_build:
            build_cable(part_number, rev_dir)

        print(_progress_bar(index, total))

    print("Finished generating all wires in family.")
    write_family_csv(list(M22759.iter_part_configurations()), family_dir)


if __name__ == "__main__":
    main()
