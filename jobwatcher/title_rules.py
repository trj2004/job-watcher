"""The intentionally broad finance-track title rule."""

import re


ROLE_PATTERN = re.compile(
    r"\b(?:"
    r"commercial\s+(?:bank(?:ing)?|lending|credit|real\s+estate|relationship)|"
    r"community\s+(?:bank(?:ing)?|development|lending|investment)|"
    r"business\s+bank(?:ing)?|"
    r"relationship\s+(?:manager|banker|associate)|"
    r"financial\s+relationship\s+consultant|"
    r"loan\s+(?:officer|originator|processor|underwriter|servicing)|"
    r"credit\s+(?:analyst|underwriter|associate|officer|risk)|"
    r"underwrit(?:er|ing)|"
    r"wealth\s+(?:management|planning|advisor|adviser)|"
    r"financial\s+(?:analyst|advisor|adviser|planning|planner|consultant)|"
    r"investment\s+(?:analyst|associate|management|manager|banking)|"
    r"portfolio\s+(?:analyst|manager|management)|"
    r"asset\s+(?:management|manager|analyst)|"
    r"risk\s+(?:analyst|manager|associate)|"
    r"treasury\s+(?:analyst|associate|management|officer)|"
    r"real\s+estate\s+(?:finance|financial|investment|analyst|acquisitions|asset|development)|"
    r"property\s+(?:management|manager)|"
    r"private\s+bank(?:er|ing)|"
    r"trust\s+(?:officer|associate|administrator)|"
    r"client\s+service\s+(?:associate|officer|manager)|"
    r"registered\s+(?:client\s+service|representative)|"
    r"affordable\s+housing\s+finance|"
    r"program\s+finance|"
    r"financial\s+services\s+(?:associate|representative|specialist)"
    r")\b",
    re.IGNORECASE,
)


def in_role(title: str) -> bool:
    """Return whether a title belongs to the current broad finance watchlist."""

    return bool(ROLE_PATTERN.search(title or ""))
