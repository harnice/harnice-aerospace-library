import re


def choose_part(
    type,
    finish,
    connector_type,
    density=None,
    wire_type=None,
    return_divider=None,
):
    """
    Choose a MIL-spec D-sub or Micro-D part number that exists in this library.

    type form:
      D{pins}{M|F}        e.g. D9M, D25F, D15M
      microD{pins}{M|F}   e.g. microD9F, microD15M, microD100F

    M is plug (pins). F is receptacle (sockets).

    D-sub (MIL-DTL-24308 Class G, no float) also needs:
      connector_type  "Crimp" or "Solder Cup"
      finish          A, F, K, T, Z
      density         "Standard" or "High" — required only when pin count
                      exists in both (15). Otherwise inferred.

    Micro-D (MIL-DTL-83513/01-/04 metal shell) also needs:
      connector_type  "Solder Cup" or "Pigtail"
      finish          A, C, K, N, P, T
      wire_type       01-16 — required for Pigtail only

    Args:
      type:             Family, pin count, and gender. See form above.
      finish:           Spec finish letter.
      connector_type:   Termination family.
      density:          D-sub contact density. Omit when unambiguous.
      wire_type:        Micro-D pigtail code (01-16).
      return_divider:   Default is underscore (M24308_2-3F_A). Pass "/" for
                        the official PIN (M24308/2-3F).

    Returns:
      Library part number string.
    """

    family, pin_count, gender = _parse_type(type)
    finish = _normalize_finish(finish)
    connector_type = _normalize_connector_type(connector_type)
    divider = "_" if return_divider is None else str(return_divider)

    if family == "D":
        return _choose_dsub(
            pin_count, gender, finish, connector_type, density, wire_type, divider
        )
    return _choose_microd(
        pin_count, gender, finish, connector_type, density, wire_type, divider
    )


# ---------------------------------------------------------------------------
# D-sub (MIL-DTL-24308) — same inventory as dsub_generator.py
# ---------------------------------------------------------------------------

# Standard: dash = shell_no. High: dash = shell_no + 10.
_DSUB_STANDARD = {9: 1, 15: 2, 25: 3, 37: 4, 50: 5}
_DSUB_HIGH = {15: 1, 26: 2, 44: 3, 62: 4, 78: 5, 104: 6}

_DSUB_SLASH = {
    ("Solder Cup", "Receptacle"): "1",
    ("Crimp", "Receptacle"): "2",
    ("Solder Cup", "Plug"): "3",
    ("Crimp", "Plug"): "4",
}

_DSUB_FINISHES = {
    "A": "pure electrodeposited aluminum",
    "F": "cadmium",
    "K": "zinc nickel",
    "T": "nickel fluorocarbon polymer",
    "Z": "zinc",
}

# High-density solder cup is not in this library (catalog pages 20-21
# are standard density only).
_DSUB_CONNECTOR_TYPES = {
    "Crimp": ("Standard", "High"),
    "Solder Cup": ("Standard",),
}


def _choose_dsub(pin_count, gender, finish, connector_type, density, wire_type, divider):
    if wire_type is not None:
        raise ValueError("wire_type applies to Micro-D pigtails only.")
    if connector_type not in _DSUB_CONNECTOR_TYPES:
        raise ValueError(
            f"Unknown D-sub connector_type {connector_type!r}. "
            f"Expected one of: {sorted(_DSUB_CONNECTOR_TYPES)}"
        )
    if finish not in _DSUB_FINISHES:
        raise ValueError(
            f"Unknown D-sub finish {finish!r}. "
            f"Expected one of: {sorted(_DSUB_FINISHES)}"
        )

    allowed_densities = _DSUB_CONNECTOR_TYPES[connector_type]
    density = _resolve_dsub_density(pin_count, density, allowed_densities)
    pin_map = _DSUB_HIGH if density == "High" else _DSUB_STANDARD
    if pin_count not in pin_map:
        raise ValueError(
            f"No {density} density D-sub with {pin_count} pins in this library. "
            f"Valid pin counts: {sorted(pin_map)}"
        )

    slash = _DSUB_SLASH[(connector_type, gender)]
    dash = pin_map[pin_count] if density == "Standard" else pin_map[pin_count] + 10
    return f"M24308{divider}{slash}-{dash}{finish}"


def _resolve_dsub_density(pin_count, density, allowed_densities):
    in_standard = pin_count in _DSUB_STANDARD and "Standard" in allowed_densities
    in_high = pin_count in _DSUB_HIGH and "High" in allowed_densities
    if density is None:
        if in_standard and in_high:
            raise ValueError(
                f"Pin count {pin_count} exists in both Standard and High density. "
                "Pass density='Standard' or density='High'."
            )
        if in_standard:
            return "Standard"
        if in_high:
            return "High"
        valid = []
        if "Standard" in allowed_densities:
            valid.extend(sorted(_DSUB_STANDARD))
        if "High" in allowed_densities:
            valid.extend(sorted(_DSUB_HIGH))
        raise ValueError(
            f"No D-sub with {pin_count} pins in this library. "
            f"Valid pin counts: {sorted(set(valid))}"
        )

    density = _normalize_density(density)
    if density not in allowed_densities:
        raise ValueError(
            f"{density} density is not available for this D-sub connector_type. "
            f"Expected one of: {list(allowed_densities)}"
        )
    if density == "Standard" and pin_count not in _DSUB_STANDARD:
        raise ValueError(
            f"No Standard density D-sub with {pin_count} pins. "
            f"Valid: {sorted(_DSUB_STANDARD)}"
        )
    if density == "High" and pin_count not in _DSUB_HIGH:
        raise ValueError(
            f"No High density D-sub with {pin_count} pins. "
            f"Valid: {sorted(_DSUB_HIGH)}"
        )
    return density


# ---------------------------------------------------------------------------
# Micro-D (MIL-DTL-83513/01-/04) — same inventory as microd_generator.py
# ---------------------------------------------------------------------------

_MICROD_INSERTS = {
    9: "A",
    15: "B",
    21: "C",
    25: "D",
    31: "E",
    37: "F",
    51: "G",
    100: "H",
}

_MICROD_SLASH = {
    ("Solder Cup", "Plug"): "01",
    ("Solder Cup", "Receptacle"): "02",
    ("Pigtail", "Plug"): "03",
    ("Pigtail", "Receptacle"): "04",
}

_MICROD_FINISHES = {
    "A": "pure electrodeposited aluminum",
    "C": "cadmium",
    "K": "zinc nickel",
    "N": "electroless nickel",
    "P": "passivated stainless steel",
    "T": "nickel fluorocarbon polymer",
}

_MICROD_WIRE_TYPES = {
    "01": "M22759/11-26-9, 18 in, white",
    "02": "M22759/11-26-9, 36 in, white",
    "03": "M22759/11-26-X, 18 in, 10-color repeating",
    "04": "M22759/11-26-X, 36 in, 10-color repeating",
    "05": "A-A-59551 25 AWG solid, 0.5 in, gold plated",
    "06": "A-A-59551 25 AWG solid, 1.0 in, gold plated",
    "07": "A-A-59551 25 AWG solid, 0.5 in, tin plated",
    "08": "A-A-59551 25 AWG solid, 1.0 in, tin plated",
    "09": "M22759/33-26-9, 18 in, white",
    "10": "M22759/33-26-9, 36 in, white",
    "11": "M22759/33-26-X, 18 in, 10-color repeating",
    "12": "M22759/33-26-X, 36 in, 10-color repeating",
    "13": "M22759/11-26-9, 72 in, white",
    "14": "M22759/11-26-X, 72 in, 10-color repeating",
    "15": "M22759/33-26-9, 72 in, white",
    "16": "M22759/33-26-X, 72 in, 10-color repeating",
}


def _choose_microd(pin_count, gender, finish, connector_type, density, wire_type, divider):
    if density is not None:
        raise ValueError("density applies to D-sub only.")
    if connector_type not in ("Solder Cup", "Pigtail"):
        raise ValueError(
            f"Unknown Micro-D connector_type {connector_type!r}. "
            "Expected one of: ['Pigtail', 'Solder Cup']"
        )
    if finish not in _MICROD_FINISHES:
        raise ValueError(
            f"Unknown Micro-D finish {finish!r}. "
            f"Expected one of: {sorted(_MICROD_FINISHES)}"
        )
    if pin_count not in _MICROD_INSERTS:
        raise ValueError(
            f"No Micro-D with {pin_count} pins in this library. "
            f"Valid pin counts: {sorted(_MICROD_INSERTS)}"
        )

    slash = _MICROD_SLASH[(connector_type, gender)]
    insert = _MICROD_INSERTS[pin_count]
    if connector_type == "Pigtail":
        wire = _normalize_wire_type(wire_type)
        return f"M83513{divider}{slash}-{insert}{wire}{finish}"
    if wire_type is not None:
        raise ValueError("wire_type applies to Micro-D pigtails only.")
    return f"M83513{divider}{slash}-{insert}{finish}"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_TYPE_RE = re.compile(
    r"^(?P<family>microd|d)(?P<pins>\d+)(?P<gender>[mf])$",
    re.IGNORECASE,
)

_CONNECTOR_TYPE_ALIASES = {
    "crimp": "Crimp",
    "solder": "Solder Cup",
    "solder cup": "Solder Cup",
    "solder-cup": "Solder Cup",
    "soldercup": "Solder Cup",
    "pigtail": "Pigtail",
    "wire": "Pigtail",
}

_DENSITY_ALIASES = {
    "standard": "Standard",
    "std": "Standard",
    "high": "High",
    "hd": "High",
}

_GENDER = {"M": "Plug", "F": "Receptacle"}


def _parse_type(type_string):
    if type_string is None:
        raise ValueError(
            "type is required. Expected D{pins}{M|F} or microD{pins}{M|F} "
            "(e.g. D9M, D25F, microD15F)."
        )
    raw = str(type_string).strip().replace(" ", "").replace("-", "")
    match = _TYPE_RE.match(raw)
    if not match:
        raise ValueError(
            f"Could not parse type {type_string!r}. "
            "Expected D{pins}{M|F} or microD{pins}{M|F} "
            "(e.g. D9M, D25F, microD15F)."
        )
    family = "microD" if match.group("family").lower() == "microd" else "D"
    pin_count = int(match.group("pins"))
    gender = _GENDER[match.group("gender").upper()]
    return family, pin_count, gender


def _normalize_finish(finish):
    if finish is None:
        raise ValueError("finish is required.")
    letter = str(finish).strip().upper()
    if len(letter) != 1 or not letter.isalpha():
        raise ValueError(
            f"Unknown finish {finish!r}. Expected a single letter."
        )
    return letter


def _normalize_connector_type(connector_type):
    if connector_type is None:
        raise ValueError(
            "connector_type is required. "
            "D-sub: Crimp or Solder Cup. Micro-D: Solder Cup or Pigtail."
        )
    key = str(connector_type).strip().lower()
    if key not in _CONNECTOR_TYPE_ALIASES:
        raise ValueError(
            f"Unknown connector_type {connector_type!r}. "
            "Expected Crimp, Solder Cup, or Pigtail."
        )
    return _CONNECTOR_TYPE_ALIASES[key]


def _normalize_density(density):
    key = str(density).strip().lower()
    if key not in _DENSITY_ALIASES:
        raise ValueError(
            f"Unknown density {density!r}. Expected Standard or High."
        )
    return _DENSITY_ALIASES[key]


def _normalize_wire_type(wire_type):
    if wire_type is None:
        raise ValueError(
            "wire_type is required for Micro-D pigtails (01-16)."
        )
    code = str(wire_type).strip()
    if code.isdigit():
        code = code.zfill(2)
    if code not in _MICROD_WIRE_TYPES:
        raise ValueError(
            f"Unknown Micro-D wire_type {wire_type!r}. "
            f"Expected one of: {sorted(_MICROD_WIRE_TYPES)}"
        )
    return code
