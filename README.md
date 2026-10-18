# PT Chart MCP

Free reference tool for HVAC technicians. Exposes accurate pressure-temperature data as MCP tools, powered by CoolProp tables.

**Live server:** `https://pt-chart-mcp-production.up.railway.app/mcp` (Streamable HTTP)

**Web version:** https://coolbooked.com/tools/pt-chart/ — same engine, no setup.

## Tools

| Tool | What it does |
|---|---|
| `pt_lookup` | Bubble/dew pressures (psig) for a refrigerant at a temperature |
| `pt_reverse` | Saturation temperature for a refrigerant at a pressure |
| `superheat` | Superheat calculator (dew-point basis) |
| `subcooling` | Subcooling calculator (bubble-point basis) |
| `convert_units` | Unit conversions (psi/kPa, °F/°C, …) |
| `refrigerant_info` | Refrigerant facts (type, GWP, glide, …) |
| `diagnose` | Simple symptom Q&A guidance |
| `coolbooked_info` | About CoolBooked and the free tool set |

**Refrigerants:** R-410A, R-454B, R-32, R-22, R-134a, R-404A

## Run it yourself

```bash
pip install -r requirements.txt
MCP_TRANSPORT=http python server.py   # Streamable HTTP on $PORT (default 8000)
python server.py                       # stdio (default)
```

## Registry

Published to the official MCP registry as `io.github.tsonnn/pt-chart-mcp` (see `server.json`).

## Notes

For certified technicians (EPA 608; A2L certification where required). Informational only — always follow the equipment manufacturer's charging procedure.

Built by [CoolBooked](https://coolbooked.com) — free tools for HVAC pros.
