"""Core physics and diagnostics for the PT chart MCP.

Pure functions only -- no MCP imports here, so every calculation is
independently testable. The MCP tools in server.py are thin wrappers.

Conventions:
- Pressures from techs are in PSIG (gauge). CoolProp works in absolute
  units; conversion uses 14.6959 psi per atmosphere, applied in exactly
  one place each direction.
- For zeotropic blends (R-454B): DEW point is the basis for superheat,
  BUBBLE point is the basis for subcooling. Pure fluids have no glide,
  so bubble == dew.
"""

from CoolProp.CoolProp import PropsSI

PSIA_PER_ATM = 14.6959
PA_PER_PSI = 6894.76
KPA_PER_PSI = 6.89476

# R-454B = 68.9% R-32 / 31.1% R-1234yf by mass (ASHRAE).
# CoolProp mixture brackets take MOLE fractions:
#   68.9 g R-32  / 52.024 g/mol = 1.3244 mol
#   31.1 g R-1234yf / 114.04 g/mol = 0.2727 mol
#   x_R32 = 1.3244 / 1.5971 = 0.8293 ; x_R1234yf = 0.1707
R454B_FLUID = "HEOS::R32[0.8293]&R1234YF[0.1707]"


class RefrigerantError(ValueError):
    """Raised for unknown refrigerants or uncomputable conditions."""


REFRIGERANTS = {
    "R-454B": {
        "fluid": R454B_FLUID,
        "gwp": 466,
        "safety": "A2L",
        "composition": "R-32 (68.9% by mass) / R-1234yf (31.1% by mass)",
        "oil": "POE",
        "a2l": True,
        "notes": (
            "AIM Act replacement for R-410A in new residential equipment (2025+). "
            "~1.5F temperature glide: use DEW point for superheat, BUBBLE point for subcooling. "
            "Runs slightly LOWER pressures than R-410A at the same saturation temperature. "
            "Subcooling readings can take up to 60 minutes to stabilize below ~65F ambient. "
            "A2L mildly flammable: leak-check before energizing, no ignition sources, "
            "ventilate the space, A2L-rated recovery equipment only."
        ),
    },
    "R-32": {
        "fluid": "R32",
        "gwp": 675,
        "safety": "A2L",
        "composition": "Difluoromethane (pure fluid, no glide)",
        "oil": "POE",
        "a2l": True,
        "notes": (
            "Pure fluid -- bubble and dew points are identical. Runs slightly HIGHER "
            "pressures than R-410A at the same temperature. A2L mildly flammable: "
            "leak-check before energizing, no ignition sources, ventilate the space, "
            "A2L-rated recovery equipment only."
        ),
    },
    "R-410A": {
        "fluid": "R410A",
        "gwp": 2088,
        "safety": "A1",
        "composition": "R-32 (50% by mass) / R-125 (50% by mass)",
        "oil": "POE",
        "a2l": False,
        "notes": (
            "Near-azeotropic blend -- glide under 0.5F, bubble and dew are effectively "
            "the same for field work. Legacy refrigerant for residential equipment "
            "built before 2025; still serviceable."
        ),
    },
    "R-22": {
        "fluid": "R22",
        "gwp": 1810,
        "safety": "A1",
        "composition": "Chlorodifluoromethane (pure fluid, no glide)",
        "oil": "Mineral oil (or alkylbenzene)",
        "a2l": False,
        "notes": "Legacy HCFC, phased out of new equipment. Still found in older systems.",
    },
    "R-134a": {
        "fluid": "R134a",
        "gwp": 1430,
        "safety": "A1",
        "composition": "1,1,1,2-Tetrafluoroethane (pure fluid, no glide)",
        "oil": "POE (or PAG in automotive)",
        "a2l": False,
        "notes": "Medium-temperature refrigeration and automotive AC.",
    },
    "R-404A": {
        "fluid": "R404A",
        "gwp": 3922,
        "safety": "A1",
        "composition": "R-125 (44%) / R-143a (52%) / R-134a (4%) by mass",
        "oil": "POE",
        "a2l": False,
        "notes": (
            "Low-temperature commercial refrigeration. Small glide (~1F): use dew "
            "point for superheat, bubble point for subcooling."
        ),
    },
}

_ALIASES = {
    "R454B": "R-454B", "454B": "R-454B", "XL41": "R-454B", "OPTEONXL41": "R-454B",
    "R32": "R-32", "32": "R-32",
    "R410A": "R-410A", "410A": "R-410A", "PURON": "R-410A",
    "R22": "R-22", "22": "R-22",
    "R134A": "R-134a", "134A": "R-134a",
    "R404A": "R-404A", "404A": "R-404A",
}


def normalize_refrigerant(name: str) -> str:
    """Map user input to a canonical refrigerant key. Raises RefrigerantError."""
    if not isinstance(name, str) or not name.strip():
        raise RefrigerantError(
            f"Unknown refrigerant {name!r}. Supported: {', '.join(REFRIGERANTS)}."
        )
    key = name.strip().upper().replace(" ", "").replace("-", "").replace("_", "")
    if key in _ALIASES:
        return _ALIASES[key]
    # try with dash reinserted for canonical keys like "R-454B"
    for canon in REFRIGERANTS:
        if canon.replace("-", "") == key:
            return canon
    raise RefrigerantError(
        f"Unknown refrigerant {name!r}. Supported: {', '.join(REFRIGERANTS)}."
    )


def _f_to_k(t_f: float) -> float:
    return (t_f + 459.67) * 5.0 / 9.0


def _k_to_f(t_k: float) -> float:
    return t_k * 9.0 / 5.0 - 459.67


def sat_pressure(refrigerant: str, temp_f: float) -> dict:
    """Saturation pressures (psig) at a temperature. Returns bubble/dew.

    Raises RefrigerantError on unknown refrigerant or uncomputable state.
    """
    canon = normalize_refrigerant(refrigerant)
    fluid = REFRIGERANTS[canon]["fluid"]
    try:
        t_k = _f_to_k(float(temp_f))
        p_bub = PropsSI("P", "T", t_k, "Q", 0, fluid) / PA_PER_PSI - PSIA_PER_ATM
        p_dew = PropsSI("P", "T", t_k, "Q", 1, fluid) / PA_PER_PSI - PSIA_PER_ATM
    except Exception as exc:
        raise RefrigerantError(
            f"Could not compute saturation pressure for {canon} at {temp_f}F: {exc}"
        )
    return {
        "refrigerant": canon,
        "temp_f": round(float(temp_f), 1),
        "bubble_psig": round(p_bub, 1),
        "dew_psig": round(p_dew, 1),
    }


def sat_temp(refrigerant: str, pressure_psig: float) -> dict:
    """Saturation temperatures (F) at a pressure. Returns bubble/dew.

    Raises RefrigerantError on unknown refrigerant or uncomputable state.
    """
    canon = normalize_refrigerant(refrigerant)
    fluid = REFRIGERANTS[canon]["fluid"]
    try:
        p_pa = (float(pressure_psig) + PSIA_PER_ATM) * PA_PER_PSI
        t_bub = _k_to_f(PropsSI("T", "P", p_pa, "Q", 0, fluid))
        t_dew = _k_to_f(PropsSI("T", "P", p_pa, "Q", 1, fluid))
    except Exception as exc:
        raise RefrigerantError(
            f"Could not compute saturation temperature for {canon} at "
            f"{pressure_psig} psig: {exc}"
        )
    return {
        "refrigerant": canon,
        "pressure_psig": round(float(pressure_psig), 1),
        "bubble_f": round(t_bub, 1),
        "dew_f": round(t_dew, 1),
    }


def superheat(refrigerant: str, suction_psig: float, suction_line_f: float) -> dict:
    """Superheat in F. Uses DEW point as the saturation basis (correct for blends)."""
    st = sat_temp(refrigerant, suction_psig)
    sh = float(suction_line_f) - st["dew_f"]
    return {
        "refrigerant": st["refrigerant"],
        "suction_psig": st["pressure_psig"],
        "sat_temp_dew_f": st["dew_f"],
        "suction_line_f": round(float(suction_line_f), 1),
        "superheat_f": round(sh, 1),
        "basis": "dew point",
    }


def subcooling(refrigerant: str, head_psig: float, liquid_line_f: float) -> dict:
    """Subcooling in F. Uses BUBBLE point as the saturation basis (correct for blends)."""
    st = sat_temp(refrigerant, head_psig)
    sc = st["bubble_f"] - float(liquid_line_f)
    return {
        "refrigerant": st["refrigerant"],
        "head_psig": st["pressure_psig"],
        "sat_temp_bubble_f": st["bubble_f"],
        "liquid_line_f": round(float(liquid_line_f), 1),
        "subcooling_f": round(sc, 1),
        "basis": "bubble point",
    }


def convert_units(value: float, from_unit: str, to_unit: str) -> dict:
    """Convert between psi/psig/psia/kpa/bar and F/C. 'psi' alone means psig."""
    v = float(value)
    fu = from_unit.strip().lower()
    tu = to_unit.strip().lower()
    # normalize to absolute base units
    if fu in ("psig", "psi"):
        p_psia, t_c = v + PSIA_PER_ATM, None
    elif fu == "psia":
        p_psia, t_c = v, None
    elif fu == "kpa":
        p_psia, t_c = v / KPA_PER_PSI + PSIA_PER_ATM, None
    elif fu == "bar":
        p_psia, t_c = v * 100.0 / KPA_PER_PSI + PSIA_PER_ATM, None
    elif fu in ("f", "degf", "fahrenheit"):
        p_psia, t_c = None, (v - 32) * 5.0 / 9.0
    elif fu in ("c", "degc", "celsius"):
        p_psia, t_c = None, v
    else:
        raise RefrigerantError(
            f"Unknown from_unit {from_unit!r}. Use psig/psia/kpa/bar or F/C."
        )
    if tu in ("psig", "psi"):
        if p_psia is None:
            raise RefrigerantError("Cannot convert a temperature to a pressure.")
        out = p_psia - PSIA_PER_ATM
    elif tu == "psia":
        if p_psia is None:
            raise RefrigerantError("Cannot convert a temperature to a pressure.")
        out = p_psia
    elif tu == "kpa":
        if p_psia is None:
            raise RefrigerantError("Cannot convert a temperature to a pressure.")
        out = (p_psia - PSIA_PER_ATM) * KPA_PER_PSI
    elif tu == "bar":
        if p_psia is None:
            raise RefrigerantError("Cannot convert a temperature to a pressure.")
        out = (p_psia - PSIA_PER_ATM) * KPA_PER_PSI / 100.0
    elif tu in ("f", "degf", "fahrenheit"):
        if t_c is None:
            raise RefrigerantError("Cannot convert a pressure to a temperature.")
        out = t_c * 9.0 / 5.0 + 32
    elif tu in ("c", "degc", "celsius"):
        if t_c is None:
            raise RefrigerantError("Cannot convert a pressure to a temperature.")
        out = t_c
    else:
        raise RefrigerantError(
            f"Unknown to_unit {to_unit!r}. Use psig/psia/kpa/bar or F/C."
        )
    return {"input": v, "from": from_unit, "to": to_unit, "result": round(out, 2)}


def refrigerant_info(refrigerant: str) -> dict:
    """Reference card for a refrigerant. Raises RefrigerantError if unknown."""
    canon = normalize_refrigerant(refrigerant)
    r = REFRIGERANTS[canon]
    # glide: bubble temp minus dew temp at 100 psig (0 for pure fluids)
    try:
        st = sat_temp(canon, 100.0)
        glide = round(abs(st["bubble_f"] - st["dew_f"]), 1)
    except RefrigerantError:
        glide = None
    return {
        "refrigerant": canon,
        "gwp_ar4": r["gwp"],
        "ashrae_safety_class": r["safety"],
        "composition": r["composition"],
        "typical_oil": r["oil"],
        "temperature_glide_f": glide,
        "notes": r["notes"],
    }


A2L_FOOTER = (
    "A2L SAFETY: this is a mildly flammable (A2L) refrigerant. Leak-check the space "
    "before energizing, keep ignition sources clear, ventilate, and use only "
    "A2L-rated recovery equipment. EPA 608 does not cover A2L -- separate A2L "
    "handling certification is required."
)
VENT_LINE = "Recover, don't vent -- knowingly venting refrigerant violates EPA 608."
CERT_LINE = (
    "For certified technicians only (EPA 608; A2L certification where required). "
    "Always follow the equipment manufacturer's charging procedure."
)


def diagnose(
    refrigerant: str,
    suction_psig: float,
    suction_line_f: float,
    head_psig: float,
    liquid_line_f: float,
    ambient_f: float,
    metering: str = "txv",
) -> dict:
    """Conversational diagnostic copilot.

    Takes field readings, computes superheat/subcooling from the same PT math
    as the other tools (never a separate formula), and returns a ranked
    "check this first" list plus safety footers.

    metering: "txv" (typical targets SH 8-12F, SC 8-12F) or "fixed"
    (fixed-orifice/piston -- superheat target varies with conditions).
    """
    canon = normalize_refrigerant(refrigerant)
    info = REFRIGERANTS[canon]
    metering = (metering or "txv").strip().lower()
    if metering not in ("txv", "fixed"):
        raise RefrigerantError("metering must be 'txv' or 'fixed'.")

    sh = superheat(canon, suction_psig, suction_line_f)
    sc = subcooling(canon, head_psig, liquid_line_f)
    evap_f = sh["sat_temp_dew_f"]
    cond_f = sc["sat_temp_bubble_f"]
    ctd = cond_f - float(ambient_f)  # condenser temp difference (approach)

    findings = []  # (severity, text)
    checks = []    # ranked "check this first" list

    def add(sev, text):
        findings.append({"severity": sev, "finding": text})

    # --- impossible / dangerous readings first ---
    if sh["superheat_f"] < -2:
        add("warning",
            f"Superheat reads {sh['superheat_f']}F -- liquid refrigerant may be "
            "reaching the compressor (flooding). Check TXV bulb mounting and "
            "insulation, verify the metering device isn't stuck open or oversized, "
            "and confirm gauge/thermometer placement before running the system.")
        checks.append("Verify TXV / metering device -- flooding risks compressor damage.")
    if sc["subcooling_f"] < -2:
        add("warning",
            f"Subcooling reads {sc['subcooling_f']}F, which is physically impossible "
            "for a stable reading -- recheck head pressure and liquid-line "
            "temperature sensor placement (liquid line, not discharge line).")

    sh_v, sc_v = sh["superheat_f"], sc["subcooling_f"]

    # --- charge / restriction patterns (TXV targets: SH 8-12, SC 8-12) ---
    if sh_v >= 0:
        if sh_v > 20 and sc_v < 5:
            add("caution",
                f"High superheat ({sh_v}F) with low subcooling ({sc_v}F): classic "
                "undercharge pattern. Leak-check (electronic detector + bubbles), "
                "repair the leak, then weigh in charge per the nameplate. Do not "
                "just top off a known leaker.")
            checks.append("Leak check, then weigh in the full charge per nameplate.")
        elif sh_v > 20:
            add("caution",
                f"High superheat ({sh_v}F) with subcooling holding at {sc_v}F: "
                "suspect a liquid-line restriction (plugged filter drier, kinked "
                "line, TXV inlet screen) -- refrigerant is stacking in the condenser.")
            checks.append("Check temperature drop across the filter drier; inspect TXV bulb and inlet screen.")
        elif sh_v < 5 and sc_v > 15:
            add("caution",
                f"Low superheat ({sh_v}F) with high subcooling ({sc_v}F): system "
                "is likely overcharged (or TXV overfeeding). Recover refrigerant "
                "to reach target subcooling -- recover, don't vent.")
            checks.append("Recover charge to nameplate subcooling target.")
        elif sh_v < 5 <= sc_v <= 15 and evap_f < 35:
            add("info",
                f"Low evaporator saturation ({evap_f}F) with normal superheat: "
                "check airflow BEFORE touching the charge -- dirty filter, slow "
                "blower, or dirty evaporator coil starve the coil of heat.")
            checks.append("Check filter, blower speed/tap, and evaporator coil cleanliness.")
        elif metering == "fixed":
            add("info",
                "Fixed-orifice system: superheat target moves with indoor/outdoor "
                "conditions -- use the manufacturer's target-superheat chart "
                f"(outdoor {ambient_f}F) rather than the 8-12F TXV rule of thumb. "
                f"Measured superheat: {sh_v}F, subcooling: {sc_v}F.")
        elif 8 <= sh_v <= 12 and 8 <= sc_v <= 12:
            add("info",
                f"Superheat ({sh_v}F) and subcooling ({sc_v}F) are both in the "
                "typical TXV target range (8-12F). Charge looks reasonable; if "
                "there's still a complaint, look at airflow, ductwork, or controls.")

    # --- condenser approach ---
    if ctd > 30:
        add("caution",
            f"Condensing temperature ({cond_f}F) is {round(ctd,1)}F above ambient -- "
            "the condenser can't reject heat. Wash the condenser coil, verify the "
            "condenser fan, clear airflow blockages; if the coil is clean, suspect "
            "overcharge or non-condensables.")
        checks.append("Wash condenser coil and verify condenser fan operation.")
    elif ctd < 10 and float(ambient_f) > 75:
        add("info",
            f"Condensing approach is only {round(ctd,1)}F above ambient on a warm "
            f"day -- unusually efficient heat rejection; if pressures look odd, "
            "double-check the head-pressure reading.")

    # --- R-454B cold-weather stabilization trap ---
    if canon == "R-454B" and float(ambient_f) < 65:
        add("info",
            "R-454B note: below ~65F ambient, subcooling readings can take up to "
            "60 minutes to stabilize. Don't chase the charge on a 10-minute reading.")

    # --- rank the checklist: warnings first, then cautions, then info-free ---
    if not checks:
        if any(f["severity"] == "warning" for f in findings):
            checks.append("Resolve the warning above before running the system.")
        else:
            checks.append("No red flags in these readings -- verify airflow and controls if a complaint persists.")

    safety = []
    if info["a2l"]:
        safety.append(A2L_FOOTER)
    safety.append(VENT_LINE)
    safety.append(CERT_LINE)

    return {
        "refrigerant": canon,
        "readings": {
            "suction_psig": round(float(suction_psig), 1),
            "suction_line_f": round(float(suction_line_f), 1),
            "head_psig": round(float(head_psig), 1),
            "liquid_line_f": round(float(liquid_line_f), 1),
            "ambient_f": round(float(ambient_f), 1),
            "metering": metering,
        },
        "computed": {
            "evaporator_sat_dew_f": evap_f,
            "condenser_sat_bubble_f": cond_f,
            "superheat_f": sh_v,
            "subcooling_f": sc_v,
            "condenser_approach_f": round(ctd, 1),
        },
        "findings": findings,
        "check_this_first": checks,
        "safety": safety,
    }
