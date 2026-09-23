import base64
import contextlib
import email.utils
import re
from typing import Literal
from urllib.parse import urlparse

import idna

from odoo.libs.debug_log import DebugLog

__all__ = [
    "address_pattern",
    "email_addr_escapes_re",
    "email_anonymize",
    "email_domain_extract",
    "email_domain_normalize",
    "email_escape_char",
    "email_normalize",
    "email_normalize_all",
    "email_re",
    "email_split",
    "email_split_and_format",
    "email_split_and_format_normalize",
    "email_split_and_normalize",
    "email_split_tuples",
    "encapsulate_email",
    "extract_rfc2822_addresses",
    "formataddr",
    "getaddresses",
    "mail_header_msgid_re",
    "parse_contact_from_email",
    "single_email_re",
    "unfold_references",
    "url_domain_extract",
]

_debug = DebugLog(__name__)


def getaddresses(fieldvalues: list[str]) -> list[tuple[str, str]]:
    return email.utils.getaddresses(fieldvalues, strict=False)


email_re = re.compile(
    r"""([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63})""", re.VERBOSE
)
single_email_re = re.compile(
    r"""^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}$""", re.VERBOSE
)
mail_header_msgid_re = re.compile(r"<[^<>]+>")
address_pattern = re.compile(r'([^" ,<@]+@[^>" ,]+)')
email_addr_escapes_re = re.compile(r'[\\"]')
_HEADER_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_FOLDING_WHITESPACE_RE = re.compile(r"[\r\n\t ]+")


def extract_rfc2822_addresses(text: str) -> list[str]:
    if not text:
        return []
    candidates = address_pattern.findall(text)
    valid_addresses = []
    for c in candidates:
        with contextlib.suppress(idna.IDNAError):
            valid_addresses.append(formataddr(("", c), charset="ascii"))
    return valid_addresses


def _normalize_email(email: str) -> str:
    local_part, at, domain = email.rpartition("@")
    if local_part.isascii():
        local_part = local_part.lower()

    return local_part + at + domain.lower()


def email_split_tuples(text: str) -> list[tuple[str, str]]:

    def _parse_based_on_spaces(pair: tuple[str, str]) -> tuple[str, str]:
        name, email = pair
        if not name and email and " " in email:
            inside_pairs = getaddresses([email.replace(" ", ",")])
            name_parts: list[str] = []
            found_email: str | Literal[False] = False
            for inner in inside_pairs:
                if inner[1] and "@" not in inner[1]:
                    name_parts.append(inner[1])
                if inner[1] and "@" in inner[1]:
                    found_email = inner[1]
            name, email = (
                (" ".join(name_parts), found_email) if found_email else (name, email)
            )
            _debug.logic(
                "email.split.space_separated",
                inner=len(inside_pairs),
                name_parts=len(name_parts),
                recovered=bool(found_email),
            )
        return (name, email)

    if not text:
        return []

    valid_pairs = [
        (addr[0], addr[1])
        for addr in getaddresses([text])
        if addr[1] and "@" in addr[1]
    ]

    if any(pair[1].startswith("@") for pair in valid_pairs):
        filtered = [
            found_email
            for found_email in email_re.findall(text)
            if found_email and not found_email.startswith("@")
        ]
        _debug.logic(
            "email.split.regex_fallback",
            pairs=len(valid_pairs),
            recovered=len(filtered),
        )
        if filtered:
            valid_pairs = [("", found_email) for found_email in filtered]

    return list(map(_parse_based_on_spaces, valid_pairs))


def email_split(text: str) -> list[str]:
    return [email for (name, email) in email_split_tuples(text)]


def email_split_and_format(text: str) -> list[str]:
    return [formataddr((name, email)) for (name, email) in email_split_tuples(text)]


def email_split_and_normalize(text: str) -> list[tuple[str, str]]:
    return [
        (name, _normalize_email(email)) for (name, email) in email_split_tuples(text)
    ]


def email_split_and_format_normalize(text: str) -> list[str]:
    return [
        formataddr((name, _normalize_email(email)))
        for (name, email) in email_split_tuples(text)
    ]


def email_normalize(text: str, strict: bool = True) -> str | Literal[False]:
    emails = email_split(text)
    if not emails or (strict and len(emails) != 1):
        _debug.logic("email.normalize.rejected", found=len(emails), strict=strict)
        return False
    return _normalize_email(emails[0])


def email_normalize_all(text: str) -> list[str]:
    return [_normalize_email(email) for email in email_split(text)]


def email_anonymize(normalized_email: str, *, redact_domain: bool = False) -> str:
    if not normalized_email:
        return normalized_email

    local, at, domain = normalized_email.partition("@")
    if len(local) <= 5:
        anon_local = local[:1] + "*" * (len(local) - 1)
    else:
        anon_local = local[:1] + "*" * (len(local) - 3) + local[-2:]

    host, dot, tld = domain.rpartition(".")
    if redact_domain and not domain.startswith("[") and all((host, dot, tld)):
        anon_host = host[0] + "*" * (len(host) - 1)
    else:
        anon_host = host

    return f"{anon_local}{at}{anon_host}{dot}{tld}"


def email_domain_extract(email: str) -> str | Literal[False]:
    normalized_email = email_normalize(email)
    if normalized_email:
        return normalized_email.rpartition("@")[2]
    return False


def email_domain_normalize(domain: str) -> str | Literal[False]:
    if not domain or "@" in domain:
        return False
    return domain.lower()


def url_domain_extract(url: str) -> str | Literal[False]:
    parser_results = urlparse(url)
    company_hostname = parser_results.hostname
    if company_hostname and "." in company_hostname:
        return ".".join(company_hostname.split(".")[-2:])
    return False


def email_escape_char(email_address: str) -> str:
    return email_address.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def formataddr(pair: tuple[str, str], charset: str = "utf-8") -> str:
    name, address = pair
    if name:
        name = _HEADER_CONTROL_RE.sub("", name)
    if address and "@" not in address:
        msg = f"invalid email address, missing '@': {address!r}"
        raise ValueError(msg)
    local, _, domain = address.rpartition("@")
    local = _HEADER_CONTROL_RE.sub("", local)
    domain = _HEADER_CONTROL_RE.sub("", domain)

    try:
        domain.encode(charset)
    except UnicodeEncodeError:
        domain = idna.encode(domain, uts46=True).decode("ascii")

    if name:
        try:
            name.encode(charset)
        except UnicodeEncodeError:
            name = base64.b64encode(name.encode("utf-8")).decode("ascii")
            return f"=?utf-8?b?{name}?= <{local}@{domain}>"
        else:
            name = email_addr_escapes_re.sub(r"\\\g<0>", name)
            return f'"{name}" <{local}@{domain}>'
    return f"{local}@{domain}"


def encapsulate_email(old_email: str, new_email: str) -> str | None:
    old_email_split = getaddresses([old_email])
    if not old_email_split:
        return old_email

    new_email_split = getaddresses([new_email])
    if not new_email_split:
        return None

    old_name, old_addr = old_email_split[0]
    if old_name:
        name_part = old_name
    else:
        name_part = old_addr.split("@")[0]

    return formataddr((name_part, new_email_split[0][1]))


def parse_contact_from_email(text: str) -> tuple[str, str]:
    if not text or not text.strip():
        return "", ""
    split_results = email_split_tuples(text)
    name, email = split_results[0] if split_results else ("", "")

    if email:
        email_normalized = email_normalize(email, strict=False) or email
    else:
        name, email_normalized = text, ""
    _debug.logic(
        "email.contact_parsed",
        candidates=len(split_results),
        has_email=bool(email),
        has_name=bool(name),
    )

    return name, email_normalized


def unfold_references(msg_references: str) -> list[str]:
    return [
        _FOLDING_WHITESPACE_RE.sub("", ref)
        for ref in mail_header_msgid_re.findall(msg_references)
    ]
