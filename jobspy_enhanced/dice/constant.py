import re

DICE_BASE_URL = "https://www.dice.com"

# Regex to filter out junk "skills" (too generic or not real skills)
SKILL_JUNK_RE = re.compile(
    r"^(years?|yrs?|experience|required|preferred|etc\.?|and|or|the|a|an|"
    r"\d+\+?\s*|\+?\d+\s*years?|skills?|qualifications?|requirements?)$",
    re.IGNORECASE,
)
