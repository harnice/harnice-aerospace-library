import re


_PN_RE = re.compile(
    r"^800-006-(06|16)(ZNU|NF|MT|Z1|C|M)(5|6|7|8|9|10|12)-(\d{1,3})([PS])([NXYZ])$"
)

_VALID_GENDERS = {"P": "S", "S": "P"}
_VALID_KEYS = {"N", "X", "Y", "Z"}
_VALID_FINISHES = {
    "C": "Aluminum / Black Anodize (Non-Conductive)",
    "M": "Aluminum / Electroless Nickel",
    "NF": "Aluminum / Cadmium with Olive Drab Chromate",
    "ZNU": "Aluminum / Zinc-Nickel with Black Chromate",
    "MT": "Aluminum / Nickel-PTFE",
    "Z1": "Stainless Steel / Passivated",
}
_VALID_RECEPTACLE_SERIES = {"800-010", "800-011"}
_VALID_RECEPTACLE_STYLES = {"01", "02", "07"}


def parse_800_006(part_number):
    """Parse a Glenair 800-006 plug part number into its how-to-order fields."""
    pn = part_number.strip().upper().replace(" ", "").replace("_", "-")
    match = _PN_RE.match(pn)
    if not match:
        raise ValueError(
            f"Could not parse '{part_number}' as a Glenair 800-006 part number. "
            "Expected format: 800-006-{06|16}{finish}{shell}-{arrangement}{P|S}{N|X|Y|Z} "
            "(e.g. 800-006-06M6-7PN_A)."
        )
    return {
        "series": "800-006",
        "shell_style": match.group(1),
        "finish": match.group(2),
        "shell_size": int(match.group(3)),
        "insert_arrangement": f"{match.group(3)}-{match.group(4)}",
        "arrangement_suffix": match.group(4),
        "contact_type": match.group(5),
        "key": match.group(6),
    }


def find_mating_connector(
    part_number,
    override_series=None,
    override_shell_style=None,
    override_finish=None,
    override_insert_arrangement=None,
    override_gender=None,
    override_keyway=None,
):
    """
    Given a Glenair 800-006 plug part number, return a mating Series 800
    receptacle part number.

    800-006 is a hex plug with integral banding platform. The default mate is
    800-010-07 (jam-nut receptacle with banding platform), opposite contact
    gender, same finish / insert / key.

    Sample plug:      800-006-06M6-7PN_A
    Default receptacle: 800-010-07M6-7SN

    Args:
      part_number:                   800-006 plug PN (spaces optional).
      override_series:               "800-010" (band platform) or "800-011"
                                     (accessory thread). Default 800-010.
      override_shell_style:          Receptacle style "01" (in-line), "02"
                                     (square flange), or "07" (jam-nut).
                                     Default "07".
      override_finish:               C, M, NF, ZNU, MT, or Z1.
      override_insert_arrangement:   e.g. "6-7".
      override_gender:               "P" or "S". Default reverses the plug.
      override_keyway:               N, X, Y, or Z. Default preserved.

    Returns:
      Mating receptacle part number string.
    """
    parsed = parse_800_006(part_number)

    series = "800-010"
    if override_series is not None:
        series = str(override_series).strip().upper().replace("_", "-")
        if series not in _VALID_RECEPTACLE_SERIES:
            raise ValueError(
                f"Unknown receptacle series '{override_series}'. "
                f"Expected one of: {sorted(_VALID_RECEPTACLE_SERIES)}"
            )

    shell_style = "07"
    if override_shell_style is not None:
        shell_style = str(override_shell_style).zfill(2)
        if shell_style not in _VALID_RECEPTACLE_STYLES:
            raise ValueError(
                f"Unknown receptacle shell style '{override_shell_style}'. "
                f"Expected one of: {sorted(_VALID_RECEPTACLE_STYLES)}"
            )

    finish = parsed["finish"]
    if override_finish is not None:
        finish = str(override_finish).upper()
        if finish not in _VALID_FINISHES:
            raise ValueError(
                f"Unknown finish '{override_finish}'. "
                f"Supported: {sorted(_VALID_FINISHES)}"
            )

    insert_arrangement = parsed["insert_arrangement"]
    if override_insert_arrangement is not None:
        insert_arrangement = str(override_insert_arrangement).strip()

    gender = _VALID_GENDERS[parsed["contact_type"]]
    if override_gender is not None:
        gender = str(override_gender).upper()
        if gender not in _VALID_GENDERS:
            raise ValueError(
                f"Unknown gender '{override_gender}'. Expected P or S."
            )

    key = parsed["key"]
    if override_keyway is not None:
        key = str(override_keyway).upper()
        if key not in _VALID_KEYS:
            raise ValueError(
                f"Unknown key '{override_keyway}'. Expected N, X, Y, or Z."
            )

    return f"{series}-{shell_style}{finish}{insert_arrangement}{gender}{key}"
