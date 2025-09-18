"""Email parsing and formatting utilities.

Pure Python email helpers with no Odoo dependencies.
"""

import base64
import email.utils
import re
from urllib.parse import urlparse

import idna
import contextlib

def getaddresses(fieldvalues):
    """Wrapper for email.utils.getaddresses with strict=False (Python 3.13+)."""
    return email.utils.getaddresses(fieldvalues, strict=False)


# Regex patterns
email_re = re.compile(
    r"""([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63})""", re.VERBOSE
)
single_email_re = re.compile(
    r"""^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}$""", re.VERBOSE
)
mail_header_msgid_re = re.compile(r"<[^<>]+>")
address_pattern = re.compile(r'([^" ,<@]+@[^>" ,]+)')
email_addr_escapes_re = re.compile(r'[\\"]')


def extract_rfc2822_addresses(text: str) -> list[str]:
    """Return a list of valid RFC 2822 addresses found in ``text``.

    Malformed addresses and non-ASCII ones are silently ignored.

    :param text: Raw text potentially containing email addresses
    :returns: List of formatted email addresses

    Example::

        >>> extract_rfc2822_addresses('admin@example.com, "bad" <>bad')
        ['admin@example.com']
    """
    if not text:
        return []
    candidates = address_pattern.findall(text)
    valid_addresses = []
    for c in candidates:
        with contextlib.suppress(idna.IDNAError):
            valid_addresses.append(formataddr(("", c), charset="ascii"))
    return valid_addresses


def _normalize_email(email: str) -> str:
    """Normalize an email address.

    As of RFC5322 section 3.4.1 local-part is case-sensitive. However most
    main providers consider the local-part as case insensitive. With SMTP-UTF8,
    this assumption may not hold for international emails. We now consider:

      * if local part is ascii: normalize to lowercase
      * else: use as-is (SMTP-UTF8 is made for non-ascii local parts)

    The domain part is always lowercased.

    :param email: Email address to normalize
    :returns: Normalized email address
    """
    local_part, at, domain = email.rpartition("@")
    try:
        local_part.encode("ascii")
    except UnicodeEncodeError:
        pass
    else:
        local_part = local_part.lower()

    return local_part + at + domain.lower()


def email_split_tuples(text: str) -> list[tuple[str, str]]:
    """Return a list of (name, email) address tuples found in text.

    Note that text should be an email header or a stringified email list
    as it may give broader results than expected on actual text.

    :param text: Text containing email addresses
    :returns: List of (name, email) tuples
    """

    def _parse_based_on_spaces(pair):
        name, email = pair
        if not name and email and " " in email:
            inside_pairs = getaddresses([email.replace(" ", ",")])
            name_parts, found_email = [], False
            for pair in inside_pairs:
                if pair[1] and "@" not in pair[1]:
                    name_parts.append(pair[1])
                if pair[1] and "@" in pair[1]:
                    found_email = pair[1]
            name, email = (
                (" ".join(name_parts), found_email) if found_email else (name, email)
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
        if filtered:
            valid_pairs = [("", found_email) for found_email in filtered]

    return list(map(_parse_based_on_spaces, valid_pairs))


def email_split(text: str) -> list[str]:
    """Return a list of the email addresses found in text.

    :param text: Text containing email addresses
    :returns: List of email addresses

    Example::

        >>> email_split('"John" <john@example.com>, jane@example.com')
        ['john@example.com', 'jane@example.com']
    """
    return [email for (name, email) in email_split_tuples(text)]


def email_split_and_format(text: str) -> list[str]:
    """Return a list of email addresses found in text, formatted using formataddr.

    :param text: Text containing email addresses
    :returns: List of formatted email addresses
    """
    return [formataddr((name, email)) for (name, email) in email_split_tuples(text)]


def email_split_and_normalize(text: str) -> list[tuple[str, str]]:
    """Same as email_split but with normalized emails.

    :param text: Text containing email addresses
    :returns: List of (name, normalized_email) tuples
    """
    return [
        (name, _normalize_email(email)) for (name, email) in email_split_tuples(text)
    ]


def email_split_and_format_normalize(text: str) -> list[str]:
    """Same as email_split_and_format but normalizing email.

    :param text: Text containing email addresses
    :returns: List of formatted, normalized email addresses
    """
    return [
        formataddr((name, _normalize_email(email)))
        for (name, email) in email_split_tuples(text)
    ]


def email_normalize(text: str, strict: bool = True) -> str | bool:
    """Sanitize and standardize email address entries.

    A normalized email is considered as:
    - having a left part + @ + a right part (the domain can be without '.something')
    - having no name before the address. Typically, having no 'Name <>'

    Example:
    - Possible Input Email: 'Name <NaMe@DoMaIn.CoM>'
    - Normalized Output Email: 'name@domain.com'

    :param text: Text containing an email address
    :param strict: If True, text should contain a single email. If more than
        one email is found, False is returned. If False, the first found
        candidate is used.
    :returns: Normalized email or False if no email found

    """
    emails = email_split(text)
    if not emails or (strict and len(emails) != 1):
        return False
    return _normalize_email(emails[0])


def email_normalize_all(text: str) -> list[str]:
    """Extract and normalize all email addresses from text.

    :param text: Text containing email addresses
    :returns: List of normalized emails found in text

    Example::

        >>> email_normalize_all('tony@e.com, "Tony2" <tony2@e.com>')
        ['tony@e.com', 'tony2@e.com']
    """
    emails = email_split(text)
    return list(filter(None, [_normalize_email(email) for email in emails]))


def email_anonymize(normalized_email: str, *, redact_domain: bool = False) -> str:
    """Replace most characters in the local part with '*' to hide the recipient.

    The email address must be normalized already.

    :param normalized_email: A normalized email address
    :param redact_domain: If True, also redact the domain part
    :returns: Anonymized email address

    Example::

        >>> email_anonymize('admin@example.com')
        'a****@example.com'
        >>> email_anonymize('portal@example.com')
        'p***al@example.com'
        >>> email_anonymize('portal@example.com', redact_domain=True)
        'p***al@e******.com'
    """
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


def email_domain_extract(email: str) -> str | bool:
    """Extract the domain from an email address.

    :param email: Email address
    :returns: Domain or False if invalid

    Example::

        >>> email_domain_extract('info@proximus.be')
        'proximus.be'
    """
    normalized_email = email_normalize(email)
    if normalized_email:
        return normalized_email.split("@")[1]
    return False


def email_domain_normalize(domain: str) -> str | bool:
    """Return the domain normalized or False if the domain is invalid.

    :param domain: Domain to normalize
    :returns: Normalized domain or False if invalid
    """
    if not domain or "@" in domain:
        return False
    return domain.lower()


def url_domain_extract(url: str) -> str | bool:
    """Extract the company domain from a URL.

    :param url: URL to extract domain from
    :returns: Domain (last two parts) or False if invalid

    Example::

        >>> url_domain_extract('https://www.info.proximus.be/page')
        'proximus.be'
    """
    parser_results = urlparse(url)
    company_hostname = parser_results.hostname
    if company_hostname and "." in company_hostname:
        return ".".join(company_hostname.split(".")[-2:])
    return False


def email_escape_char(email_address: str) -> str:
    """Escape problematic characters in the given email address string.

    :param email_address: Email address to escape
    :returns: Escaped email address
    """
    return email_address.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def formataddr(pair: tuple[str, str], charset: str = "utf-8") -> str:
    """Pretty format a 2-tuple of the form (realname, email_address).

    If the first element of pair is falsy then only the email address is returned.

    Set the charset to ascii to get a RFC-2822 compliant email. The realname
    will be base64 encoded (if necessary) and the domain part of the email
    will be punycode encoded (if necessary).

    :param pair: Tuple of (name, email_address)
    :param charset: Character set to use (default: 'utf-8')
    :returns: Formatted email address

    Example::

        >>> formataddr(('John Doe', 'johndoe@example.com'))
        '"John Doe" <johndoe@example.com>'
        >>> formataddr(('', 'johndoe@example.com'))
        'johndoe@example.com'
    """
    name, address = pair
    local, _, domain = address.rpartition("@")

    try:
        domain.encode(charset)
    except UnicodeEncodeError:
        domain = idna.encode(domain).decode("ascii")

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
    """Change the FROM of the message and use the old one as name.

    :param old_email: Original email address (with optional name)
    :param new_email: New email address
    :returns: Formatted email with old name and new address

    Example::

        >>> encapsulate_email('"Admin" <admin@gmail.com>', 'notifications@odoo.com')
        '"Admin" <notifications@odoo.com>'
    """
    old_email_split = getaddresses([old_email])
    if not old_email_split or not old_email_split[0]:
        return old_email

    new_email_split = getaddresses([new_email])
    if not new_email_split or not new_email_split[0]:
        return None

    old_name, old_addr = old_email_split[0]
    if old_name:
        name_part = old_name
    else:
        name_part = old_addr.split("@")[0]

    return formataddr((name_part, new_email_split[0][1]))


def parse_contact_from_email(text: str) -> tuple[str, str]:
    """Parse contact name and email from text.

    Supported syntax:
    - Raoul <raoul@grosbedon.fr>
    - "Raoul le Grand" <raoul@grosbedon.fr>
    - Raoul raoul@grosbedon.fr

    Otherwise: default, text is set as name.

    :param text: Text containing contact information
    :returns: Tuple of (name, normalized_email)
    """
    if not text or not text.strip():
        return "", ""
    split_results = email_split_tuples(text)
    name, email = split_results[0] if split_results else ("", "")

    if email:
        email_normalized = email_normalize(email, strict=False) or email
    else:
        name, email_normalized = text, ""

    return name, email_normalized


def unfold_references(msg_references: str) -> list[str]:
    r"""Unfold RFC2822 header bodies that may be "folded" using CRLF+WSP.

    Some mail clients split References header body which contains
    Message Ids by "\\n ".

    :param msg_references: References header value
    :returns: List of unfolded message IDs
    """
    return [
        re.sub(r"[\r\n\t ]+", r"", ref)
        for ref in mail_header_msgid_re.findall(msg_references)
    ]
