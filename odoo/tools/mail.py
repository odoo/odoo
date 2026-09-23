import random
import socket
import time
from email.message import Message as EmailMessage

from odoo.libs.email import (
    email_anonymize,
    email_domain_extract,
    email_domain_normalize,
    email_normalize,
    email_normalize_all,
    email_re,
    email_split,
    email_split_and_format,
    email_split_and_format_normalize,
    email_split_and_normalize,
    email_split_tuples,
    encapsulate_email,
    formataddr,
    getaddresses,
    mail_header_msgid_re,
    parse_contact_from_email,
    single_email_re,
    unfold_references,
    url_domain_extract,
)
from odoo.libs.text import (
    HTML_TAG_URL_REGEX,
    SANITIZE_TAGS,
    TEXT_URL_REGEX,
    URL_REGEX,
    URL_SKIP_PROTOCOL_REGEX,
    add_html_content,
    create_link,
    fromstring,
    html2plaintext,
    html_escape,
    html_keep_url,
    html_normalize,
    html_sanitize,
    html_to_inner_content,
    is_html_empty,
    normalize_url,
    plaintext2html,
    prepend_html_content,
    replace_local_links,
    safe_attrs,
)

__all__ = [
    "HTML_TAG_URL_REGEX",
    "SANITIZE_TAGS",
    "TEXT_URL_REGEX",
    "URL_REGEX",
    "URL_SKIP_PROTOCOL_REGEX",
    "add_html_content",
    "create_link",
    "decode_message_header",
    "email_anonymize",
    "email_domain_extract",
    "email_domain_normalize",
    "email_normalize",
    "email_normalize_all",
    "email_re",
    "email_split",
    "email_split_and_format",
    "email_split_and_format_normalize",
    "email_split_and_normalize",
    "email_split_tuples",
    "encapsulate_email",
    "formataddr",
    "fromstring",
    "generate_tracking_message_id",
    "getaddresses",
    "html2plaintext",
    "html_escape",
    "html_keep_url",
    "html_normalize",
    "html_sanitize",
    "html_to_inner_content",
    "is_html_empty",
    "mail_header_msgid_re",
    "normalize_url",
    "parse_contact_from_email",
    "plaintext2html",
    "prepend_html_content",
    "replace_local_links",
    "safe_attrs",
    "single_email_re",
    "unfold_references",
    "url_domain_extract",
]


def generate_tracking_message_id(res_id: int | str) -> str:
    try:
        rnd = random.SystemRandom().random()
    except NotImplementedError:
        rnd = random.random()
    rndstr = ("%.15f" % rnd)[2:]
    return "<%s.%.15f-odoo-%s@%s>" % (
        rndstr,
        time.time(),
        res_id,
        socket.gethostname(),
    )


def decode_message_header(
    message: EmailMessage, header: str, separator: str = " "
) -> str:
    return separator.join(h for h in message.get_all(header, []) if h)
