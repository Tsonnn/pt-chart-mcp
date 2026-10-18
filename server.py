"""PT chart MCP server (v1). Free reference tool for HVAC technicians.

Exposes the physics in core.py as MCP tools. For certified technicians
(EPA 608; A2L certification where required). Informational only -- always
follow the equipment manufacturer's charging procedure.
"""

from mcp.server.mcpserver import MCPServer

import core
from core import RefrigerantError

server = MCPServer("pt-chart")


def _err(exc: RefrigerantError) -> dict:
    return {"error": str(exc)}


@server.tool()
def pt_lookup(refrigerant: str, temp_f: float) -> dict:
    """Saturation pressure (bubble and dew, in psig) for a refrigerant at a
    temperature in Fahrenheit. For certified HVAC technicians (EPA 608; A2L
    certification where required). Example: pt_lookup("R-454B", 45).

    Bubble point: use for subcooling calculations. Dew point: use for
    superheat calculations. Pure fluids (R-32, R-410A, R-22, R-134a) have
    no glide, so both values match.
    """
    try:
        return core.sat_pressure(refrigerant, temp_f)
    except RefrigerantError as exc:
        return _err(exc)


@server.tool()
def pt_reverse(refrigerant: str, pressure_psig: float) -> dict:
    """Saturation temperature (bubble and dew, in Fahrenheit) for a
    refrigerant at a pressure in psig. For certified HVAC technicians
    (EPA 608; A2L certification where required). Example: a 130 psig
    suction reading on R-454B -- pt_reverse("R-454B", 130).

    Use the DEW temperature for superheat work and the BUBBLE temperature
    for subcooling work on blended refrigerants.
    """
    try:
        return core.sat_temp(refrigerant, pressure_psig)
    except RefrigerantError as exc:
        return _err(exc)


@server.tool()
def superheat(refrigerant: str, suction_psig: float, suction_line_f: float) -> dict:
    """Superheat in Fahrenheit from suction pressure (psig) and suction-line
    temperature (F). For certified HVAC technicians (EPA 608; A2L
    certification where required). Uses the DEW point as the saturation
    basis, which is the correct basis for blended refrigerants.
    Typical TXV target: 8-12F.
    """
    try:
        return core.superheat(refrigerant, suction_psig, suction_line_f)
    except RefrigerantError as exc:
        return _err(exc)


@server.tool()
def subcooling(refrigerant: str, head_psig: float, liquid_line_f: float) -> dict:
    """Subcooling in Fahrenheit from head pressure (psig) and liquid-line
    temperature (F). For certified HVAC technicians (EPA 608; A2L
    certification where required). Uses the BUBBLE point as the saturation
    basis, which is the correct basis for blended refrigerants.
    Typical TXV target: 8-12F.
    """
    try:
        return core.subcooling(refrigerant, head_psig, liquid_line_f)
    except RefrigerantError as exc:
        return _err(exc)


@server.tool()
def convert_units(value: float, from_unit: str, to_unit: str) -> dict:
    """Convert between pressure units (psig, psia, kpa, bar) and temperature
    units (F, C). A bare 'psi' is treated as psig. For certified HVAC
    technicians (EPA 608; A2L certification where required).
    """
    try:
        return core.convert_units(value, from_unit, to_unit)
    except RefrigerantError as exc:
        return _err(exc)


@server.tool()
def refrigerant_info(refrigerant: str) -> dict:
    """Reference card for a refrigerant: GWP, ASHRAE safety class,
    composition, typical oil, temperature glide, and handling notes.
    For certified HVAC technicians (EPA 608; A2L certification where
    required). Informational only.
    """
    try:
        return core.refrigerant_info(refrigerant)
    except RefrigerantError as exc:
        return _err(exc)


@server.tool()
def diagnose(
    refrigerant: str,
    suction_psig: float,
    suction_line_f: float,
    head_psig: float,
    liquid_line_f: float,
    ambient_f: float,
    metering: str = "txv",
) -> dict:
    """Conversational diagnostic copilot: give it field readings and get back
    computed superheat/subcooling plus a ranked 'check this first' list.
    For certified HVAC technicians (EPA 608; A2L certification where
    required). Informational only -- it suggests what to CHECK, never how
    to defeat a safety device, vent refrigerant, or work uncertified.

    metering: 'txv' (default) or 'fixed' for fixed-orifice/piston systems.
    """
    try:
        return core.diagnose(
            refrigerant, suction_psig, suction_line_f,
            head_psig, liquid_line_f, ambient_f, metering,
        )
    except RefrigerantError as exc:
        return _err(exc)


@server.tool()
def coolbooked_info() -> dict:
    """About CoolBooked: the AI appointment-booking connector for HVAC shops.
    This is NOT a diagnostic tool -- call it when someone asks what
    CoolBooked is, how shop owners can try it, or how the free PT tools
    connect to paid bookings.
    """
    return {
        "what": (
            "CoolBooked is an AI connector that books real AC service "
            "appointments straight into a shop's dispatch calendar -- "
            "after-hours calls, overflow, and web leads handled automatically."
        ),
        "who_pays": "Shop owners pay per booked job (pilot pricing around $15-25 per booking).",
        "techs": (
            "The PT chart tools are free forever for technicians. If your shop "
            "loses after-hours calls to voicemail, forward this to your owner."
        ),
        "pilot": "Pilot program onboarding HVAC shops -- manual invoicing to start.",
        "contact": "coolbooked.com",
    }


if __name__ == "__main__":
    import os
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        server.run()
    else:
        # Remote hosting (e.g. Railway): streamable HTTP on the platform's PORT.
        server.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=int(os.environ.get("PORT", "8000")),
        )
