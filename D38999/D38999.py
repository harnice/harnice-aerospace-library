import re


def find_mating_connector(
    part_number,
    override_shell_style = None,
    override_finish = None,
    override_insert_arrangement = None,
    override_gender = None,
    override_keyway = None,
    return_divider = None
    ):
    """
    Given a MIL-DTL-38999 part number, returns the mating connector part number
    as a string in D38999_ format.

    Supports a number of prefixes.
    Supports Series I, II, III, and IV style codes.

    D38999 Series III part number structure (after the style code):
      [Shell Style 1] [Contact Style 1] [Insert Arrangement 2-3] [Shell Material 1] [Key 1]
      e.g. /26 F G16 S N
            ^  ^  ^^ ^ ^
            |  |  |  | └─ Master keyway arrangement
            |  |  |  └─── Pins or Sockets
            |  |  └────── Insert arrangement (2-3 digits)
            |  └───────── Finish
            └──────────── Shell style

    Args:
      part_number:                      The MIL-DTL-38999 part number string you want a match to.
      override_shell_style:             Assert a shell style. See the lookup table for the complete set but if yours is a 26, you'll get a 24 or if it's a 20 or 24 you'll get a 26.
      override_finish:                  Assert a finish. Default will stay the same as yours.
      override_insert_arrangement:      Assert an insert arrangement. Default will stay the same as yours.
      override_gender:                  Assert pins/sockets. Default will reverse yours.
      override_keyway:                  Assert a master keyway. Default will stay the same as yours.
      return_divider:                   By default, Harnice will return an underscore D38999_xxxxxx. Change that here. 

    Returns:
      Mating part number string in D38999_ format.
    """

    mating_shell_styles = {  # given a shell size in the input, what shell size should be returned
        # Series I
        "01": "13",
        "03": "15",
        "05": "17",
        "13": "01",
        "15": "03",
        "17": "05",
        # Series II
        "11": "33",
        "33": "11",
        # Series III
        "20": "26",
        "24": "26",
        "26": "24",
        # Series IV
        "41": "53",
        "43": "55",
        "53": "41",
        "55": "43",
    }

    valid_finishes = {
        "A": "Cadmium olive drab",
        "B": "Cadmium clear/bright",
        "C": "Zinc-nickel olive drab",
        "D": "Electroless nickel",
        "E": "Anodized (aluminum)",
        "F": "Black anodized (aluminum)",
        "G": "Nickel PTFE",
        "H": "Hard anodized",
        "N": "Electroless nickel",
        "S": "Stainless passivated",
        "W": "Nickel",
        "Y": "Cadmium yellow chromate",
        "Z": "Zinc-nickel black",
    }

    valid_genders = {"P": "S", "S": "P"}

    # Normalize - accept various input formats
    pn = (
        part_number.strip().upper().replace(" ", "")
    )  # force input to caps, remove spaces
    pn = pn.replace("_", "/").replace("-", "/") # allow underscore or dash in leading name
    pn = pn.replace("MS38999", "D38999")  # allow MS38999
    pn = pn.replace("MIL-DTL-38999", "D38999") # allow MIL-DTL-38999

    match = re.match(r"^D38999/(\d{2})([A-Z])([A-Z])(\d{1,2})([A-Z])([A-Z])$", pn)
    if not match:
        raise ValueError(
            f"Could not parse '{part_number}' as a MIL-DTL-38999 part number. "
            "Expected format: D38999/XX[shell_style][contact][insert][material][key] "
            "(e.g. D38999/26FG16SN)."
        )

    shell_style = match.group(1)  # e.g. "26"
    finish = match.group(2)  # e.g. "F"
    shell_size = match.group(3)  # e.g. "G" (gender: A=pin, B=socket... or other)
    insert_arrangement_suffix = match.group(4)  # e.g. "16"
    insert_arrangement = f"{shell_size}{insert_arrangement_suffix}"
    gender = match.group(5)  # e.g. "S"
    key = match.group(6)  # e.g. "N"

    if shell_style not in mating_shell_styles:
        raise ValueError(
            f"Unknown shell style '{shell_style}'. "
            f"Supported shell styles: {sorted(mating_shell_styles.keys())}"
        )
    mating_shell_style = mating_shell_styles.get(shell_style)
    if override_shell_style:
        mating_shell_style = override_shell_style

    # Preserve finish
    if finish not in valid_finishes:
        raise ValueError(
            f"Unknown shell style '{shell_style}'. "
            f"Supported shell styles: {sorted(mating_shell_styles.keys())}"
        )
    mating_finish = finish
    if override_finish:
        mating_finish = override_finish

    # Preserve insert arrangement
    mating_insert_arrangement = insert_arrangement
    if override_insert_arrangement:
        mating_insert_arrangement = override_insert_arrangement

    # Flip contact gender
    if gender not in valid_genders:
        raise ValueError(
            f"Unknown gender '{shell_style}'. "
            f"Supported genders: {sorted(mating_shell_styles.keys())}"
        )
    mating_gender = valid_genders.get(gender)
    if override_gender:
        mating_gender = override_gender

    # Preserve key
    mating_key = key
    if override_keyway:
        mating_key = override_keyway

    if return_divider:
        divider = return_divider
    else:
        divider = "_"

    return f"D38999{divider}{mating_shell_style}{mating_finish}{mating_insert_arrangement}{mating_gender}{mating_key}"


def find_backshell(
    part_number,
    orientation,
    override_shell_size=None,
    override_finish=None,
    override_entry_size=None,
    override_detent=None,
    override_basic=None,
):
    """
    Given a MIL-DTL-38999 part number, returns a matching M85049 banding
    backshell part number (AS85049/88, /89, or /90 — designator H).

    Shell size and finish are derived from the connector part number.
    Orientation is required.

    Part number format returned (matches M85049/ library):
      M85049-{88|89|90}_{N?}{shell}{finish}{entry}
      e.g. M85049-88_17F03_A, M85049-90_9Z03_A

    Args:
      part_number:          MIL-DTL-38999 part number (e.g. D38999/26FG16SN).
      orientation:          Required. One of "straight", "45_deg", "90_deg".
      override_shell_size:  Assert shell size (9, 11, 13, 15, 17, 19, 21, 23, 25).
      override_finish:      Assert M85049 finish code (F, G, N, P, W, X, YP, Z, ZP).
      override_entry_size:  Assert cable entry ("02" or "03"). Default is "03".
      override_detent:      Assert detent: "" for detented, "N" for non-detented.
                            Default is "" (detented).
      override_basic:       Assert slash number directly ("88", "89", or "90").

    Returns:
      Backshell part number string.
    """

    orientation_to_basic = {
        "straight": "88",
        "45_deg": "89",
        "90_deg": "90",
    }

    # Series III letter (insert arrangement prefix) → M85049 numeric shell size
    letter_to_shell_size = {
        "A": 9,
        "B": 11,
        "C": 13,
        "D": 15,
        "E": 17,
        "F": 19,
        "G": 21,
        "H": 23,
        "J": 25,
    }

    # D38999 finish → closest M85049/88-90 aluminum finish
    finish_to_m85049 = {
        "A": "W",   # Cadmium olive drab → Cadmium olive drab
        "B": "W",   # Cadmium clear → Cadmium olive drab (nearest cad)
        "C": "Z",   # Zinc-nickel olive drab → Zinc nickel
        "D": "N",   # Electroless nickel → Electroless nickel
        "E": "N",   # Anodized → Electroless nickel (nearest common)
        "F": "F",   # → Stainless steel
        "G": "X",   # Nickel PTFE → Nickel fluorocarbon polymer
        "H": "N",   # Hard anodized → Electroless nickel
        "K": "N",   # Common Series III code treated as electroless nickel family
        "N": "N",   # Electroless nickel → Electroless nickel
        "S": "N",   # Stainless passivated → Electroless nickel (nearest)
        "W": "N",   # Nickel → Electroless nickel
        "Y": "P",   # Cadmium yellow → Cad olive drab selective (P)
        "Z": "Z",   # Zinc-nickel black → Zinc nickel
    }

    valid_m85049_finishes = {"F", "G", "N", "P", "W", "X", "YP", "Z", "ZP"}

    # Entry sizes available per shell (Table I); 02 is N/A on 9 and 11
    valid_entries_by_shell = {
        9: ["03"],
        11: ["03"],
        13: ["02", "03"],
        15: ["02", "03"],
        17: ["02", "03"],
        19: ["02", "03"],
        21: ["02", "03"],
        23: ["02", "03"],
        25: ["02", "03"],
    }

    if orientation not in orientation_to_basic:
        raise ValueError(
            f"Unknown orientation '{orientation}'. "
            f"Expected one of: {sorted(orientation_to_basic.keys())}"
        )
    basic = orientation_to_basic[orientation]
    if override_basic is not None:
        basic = str(override_basic)
        if basic not in orientation_to_basic.values():
            raise ValueError(
                f"Unknown basic '{basic}'. Expected one of: 88, 89, 90"
            )

    # Normalize connector PN — same rules as find_mating_connector
    pn = part_number.strip().upper().replace(" ", "")
    pn = pn.replace("_", "/").replace("-", "/")
    pn = pn.replace("MS38999", "D38999")
    pn = pn.replace("MIL-DTL-38999", "D38999")

    match = re.match(r"^D38999/(\d{2})([A-Z])([A-Z])(\d{1,2})([A-Z])([A-Z])$", pn)
    if not match:
        raise ValueError(
            f"Could not parse '{part_number}' as a MIL-DTL-38999 part number. "
            "Expected format: D38999/XX[finish][shell_letter][insert][gender][key] "
            "(e.g. D38999/26FG16SN)."
        )

    connector_finish = match.group(2)  # e.g. "F"
    shell_letter = match.group(3)  # e.g. "G" → size 21

    if shell_letter not in letter_to_shell_size:
        raise ValueError(
            f"Unknown shell size letter '{shell_letter}'. "
            f"Supported: {sorted(letter_to_shell_size.keys())}"
        )
    shell_size = letter_to_shell_size[shell_letter]
    if override_shell_size is not None:
        shell_size = int(override_shell_size)
        if shell_size not in valid_entries_by_shell:
            raise ValueError(
                f"Unknown shell size '{shell_size}'. "
                f"Supported: {sorted(valid_entries_by_shell.keys())}"
            )

    if connector_finish not in finish_to_m85049:
        raise ValueError(
            f"Unknown connector finish '{connector_finish}'. "
            f"Supported: {sorted(finish_to_m85049.keys())}"
        )
    finish = finish_to_m85049[connector_finish]
    if override_finish is not None:
        finish = str(override_finish).upper()
        if finish not in valid_m85049_finishes:
            raise ValueError(
                f"Unknown M85049 finish '{finish}'. "
                f"Supported: {sorted(valid_m85049_finishes)}"
            )

    # Default cable entry 03
    entry_size = "03"
    if override_entry_size is not None:
        entry_size = str(override_entry_size).zfill(2)
    if entry_size not in valid_entries_by_shell[shell_size]:
        raise ValueError(
            f"Entry size '{entry_size}' is not valid for shell size {shell_size}. "
            f"Valid: {valid_entries_by_shell[shell_size]}"
        )

    # Default detented (blank)
    if override_detent is None:
        detent = ""
    else:
        detent = str(override_detent).upper()
        if detent in ("", "-", "--", "NONE", "DETENTED"):
            detent = ""
        elif detent != "N":
            raise ValueError(
                f"Unknown detent '{override_detent}'. "
                "Use '' for detented or 'N' for non-detented."
            )

    return f"M85049-{basic}_{detent}{shell_size}{finish}{entry_size}"
