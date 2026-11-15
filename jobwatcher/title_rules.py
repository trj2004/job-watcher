"""The intentionally broad finance-track title rule."""

import re


ROLE_PATTERN = re.compile(
    r"\b(?:"
    r"commercial\s+(?:bank(?:ing)?|lending|credit|real\s+estate)|"
    r"community\s+(?:bank(?:ing)?|development|lending)|"
    r"business\s+bank(?:ing)?|"
    r"relationship\s+manager|"
    r"loan\s+officer|"
    r"credit\s+(?:analyst|underwriter|associate)|"
    r"wealth\s+(?:management|planning)|"
    r"financial\s+(?:analyst|advisor|adviser|planning|consultant)|"
    r"investment\s+(?:analyst|associate)|"
    r"portfolio\s+(?:analyst|manager)|"
    r"risk\s+analyst|"
    r"treasury\s+(?:analyst|associate)|"
    r"real\s+estate\s+(?:finance|financial|investment|analyst)|"
    r"affordable\s+housing\s+finance|"
    r"program\s+finance"
    r")\b",
    re.IGNORECASE,
)


def in_role(title: str) -> bool:
    """Return whether a title belongs to the current broad finance watchlist."""

    return bool(ROLE_PATTERN.search(title or ""))
