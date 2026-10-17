import re


_PN_RE = re.compile(
    r"^(?:OST-)?(?P<tc_type>RS|R/S|R|S|K|T|J|E|N|C|D|G|U|B)-"
    r"(?P<gender>MALE|FEMALE|PLUG|JACK|SOCKET|RECEPTACLE|PIN|M|F|P|S)$",
    re.IGNORECASE,
)

# ASTM E1129 uses one connector for R and S, and uncompensated Cu/Cu (U) for B.
_TYPE_ALIASES = {
    "R": "RS",
    "S": "RS",
    "R/S": "RS",
    "RS": "RS",
    "B": "U",
}

_VALID_TYPES = {"K", "T", "J", "E", "N", "RS", "C", "D", "G", "U"}

_GENDER_ALIASES = {
    "M": "M",
    "MALE": "M",
    "PLUG": "M",
    "PIN": "M",
    "P": "M",
    "F": "F",
    "FEMALE": "F",
    "JACK": "F",
    "SOCKET": "F",
    "S": "F",
    "RECEPTACLE": "F",
}


def choose_part(tc_type, gender="M", return_divider=None):
    """
    Choose a standard-size (ASTM E1129 / Omega OST) thermocouple connector
    that exists in this library.

    tc_type:
      K, T, J, E, N, C, D, G, U, RS (or R, S, R/S), B
      R and S share one connector (green). B uses the uncompensated U
      (white, copper/copper) connector.

    gender:
      M / male / plug / pin     — two round prongs (negative is larger)
      F / female / jack / socket

    return_divider:
      Default library PNs use a filesystem-safe code (OST-RS-M_A).
      Pass "/" to return the Omega catalog PIN (OST-R/S-M). Other types
      are unchanged.

    Returns:
      Library part number string, e.g. OST-K-M_A.
    """
    code = _normalize_type(tc_type)
    sex = _normalize_gender(gender)
    return _format_pn(code, sex, return_divider)


def find_mating_connector(part_number, override_gender=None, return_divider=None):
    """
    Given an OST part number, return the mating connector of the opposite
    gender, same thermocouple type.

    Sample: OST-K-M_A  ->  OST-K-F_A
    """
    parsed = parse_ost(part_number)
    gender = parsed["gender"]
    if override_gender is None:
        gender = "F" if gender == "M" else "M"
    else:
        gender = _normalize_gender(override_gender)
    return _format_pn(parsed["tc_type"], gender, return_divider)


def parse_ost(part_number):
    """Parse an OST / library thermocouple connector part number."""
    pn = str(part_number).strip().upper().replace(" ", "").replace("_", "-")
    pn = pn.replace("R/S", "RS")
    match = _PN_RE.match(pn)
    if not match:
        raise ValueError(
            f"Could not parse {part_number!r} as a standard thermocouple "
            "connector. Expected OST-{{type}}-{{M|F}}, e.g. OST-K-M_A."
        )
    return {
        "series": "OST",
        "tc_type": _normalize_type(match.group("tc_type")),
        "gender": _normalize_gender(match.group("gender")),
    }


def _normalize_type(tc_type):
    code = str(tc_type).strip().upper().replace("TYPE", "").replace(" ", "")
    code = code.replace("_", "").replace("-", "")
    code = _TYPE_ALIASES.get(code, code)
    if code not in _VALID_TYPES:
        raise ValueError(
            f"Unknown thermocouple type {tc_type!r}. "
            f"Expected one of: {sorted(_VALID_TYPES)} (R, S, B also accepted)."
        )
    return code


def _normalize_gender(gender):
    key = str(gender).strip().upper().replace(" ", "").replace("-", "")
    if key not in _GENDER_ALIASES:
        raise ValueError(
            f"Unknown gender {gender!r}. Expected M/F, male/female, "
            "plug/jack, or pin/socket."
        )
    return _GENDER_ALIASES[key]


def _format_pn(tc_type, gender, return_divider):
    if return_divider == "/" and tc_type == "RS":
        return f"OST-R/S-{gender}"
    return f"OST-{tc_type}-{gender}"
