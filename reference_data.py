"""Manufacturer/published reference points for the accuracy gate.

Each entry: (refrigerant, temp_f, bubble_psig, dew_psig_or_None, source).

Gate: computed value must be within +/-2 psi of the reference.

IMPORTANT CORRECTION (found during v1 validation, 2026-10-17):
The gesonchiller.com R-454B table cited in the original plan is WRONG at
operating temperatures (e.g. it claims 293/283 psig bubble/dew at 80F).
That is thermodynamically impossible for this blend: R-454B is 83 mol%
R-32, and pure R-32 saturates at 241.5 psig at 80F. A zeotropic blend with
~1.5F glide (near-ideal behavior) cannot have a bubble pressure 50 psi
ABOVE its dominant pure component. The manufacturer authorities below
(Chemours PIB, Allied Air manual) plus the published normal boiling point
all agree with the CoolProp mixture model within ~2 psi, so the blog
table is rejected and NOT used as reference.
"""

# (refrigerant, temp_F, bubble_psig, dew_psig, source)
REFERENCE_POINTS = [
    # R-410A -- Chemours OPTXLPTAC-2 (Apr 2025), via vifalio.com; 45F field anchor
    ("R-410A", 40, 118.4, 118.4, "Chemours OPTXLPTAC-2 via vifalio.com"),
    ("R-410A", 45, 130.0, 130.0, "field-standard anchor (~130 psig at 45F)"),
    ("R-410A", 80, 236.5, 236.5, "Chemours OPTXLPTAC-2 via vifalio.com"),
    ("R-410A", 100, 318.5, 318.5, "Chemours OPTXLPTAC-2 via vifalio.com"),
    # R-32 -- hudsontech.com PT chart
    ("R-32", 40, 121.0, 121.0, "hudsontech.com R-32 PT chart"),
    ("R-32", 45, 133.0, 133.0, "hudsontech.com R-32 PT chart"),
    ("R-32", 80, 241.5, 241.5, "hudsontech.com R-32 PT chart"),
    ("R-32", 100, 325.7, 325.7, "hudsontech.com R-32 PT chart"),
    # R-454B -- Chemours Opteon XL41 PIB (bubble @77F, normal boiling point)
    # and Allied Air Enterprises R-454B piping guidelines (bubble @93F).
    # The gesonchiller.com table is REJECTED (see module docstring).
    ("R-454B", 77, 213.1, None, "Chemours Opteon XL41 PIB: vapor pressure sat. liquid at 25C"),
    ("R-454B", 93, 272.0, None, "Allied Air Enterprises R-454B piping guidelines Table 6"),
    # R-22 -- Chemours-sourced table via vifalio.com
    ("R-22", 40, 68.6, 68.6, "vifalio.com (Chemours-sourced)"),
    ("R-22", 100, 195.9, 195.9, "vifalio.com (Chemours-sourced)"),
    # R-134a -- field-standard anchors
    ("R-134a", 0, 6.5, 6.5, "field-standard anchor"),
    ("R-134a", 40, 35.0, 35.0, "field-standard anchor"),
    # R-404A -- mymortuarycooler.com (states NIST REFPROP-based, matches Arkema)
    ("R-404A", 0, 33.7, 32.6, "mymortuarycooler.com (NIST-based)"),
    ("R-404A", 40, 86.9, 85.4, "mymortuarycooler.com (NIST-based)"),
    ("R-404A", 80, 175.4, 173.4, "mymortuarycooler.com (NIST-based)"),
]

# Normal boiling point check: (refrigerant, expected_bubble_temp_F_at_0psig, source)
BOILING_POINTS = [
    ("R-454B", -58.9, "Chemours Opteon XL41 PIB"),
]

TOLERANCE_PSI = 2.0
TOLERANCE_TEMP_F = 1.0
