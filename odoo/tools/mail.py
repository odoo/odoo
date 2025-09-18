# ruff: noqa: F401
"""
Odoo mail utilities.

This module combines HTML utilities from odoo.libs.text.html with
email utilities from odoo.libs.email for Odoo-specific mail handling.
"""

import random
import socket
import time

from odoo.libs.email import (
    email_addr_escapes_re,
    email_anonymize,
    email_domain_extract,
    email_domain_normalize,
    email_escape_char,
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
    mail_header_msgid_re,
    parse_contact_from_email,
    single_email_re,
    unfold_references,
    url_domain_extract,
)

# Also import internal function for backward compatibility
from odoo.libs.email.parsing import _normalize_email, getaddresses

# Import all HTML utilities from libs/text/html for backward compatibility
from odoo.libs.text.html import (
    HTML_NEWLINES_REGEX,
    HTML_TAG_URL_REGEX,
    HTML_TAGS_REGEX,
    SANITIZE_TAGS,
    TEXT_URL_REGEX,
    URL_REGEX,
    # URL regex constants (used by sms, link_tracker modules)
    URL_SKIP_PROTOCOL_REGEX,
    append_content_to_html,
    create_link,
    fromstring,
    # HTML/Text conversion
    html2plaintext,
    html_escape,
    html_keep_url,
    html_normalize,
    # Sanitization
    html_sanitize,
    html_to_inner_content,
    is_html_empty,
    plaintext2html,
    prepend_html_content,
    safe_attrs,
    tag_quote,
    validate_url,
)

__all__ = [
    "email_domain_extract",
    "email_domain_normalize",
    "email_normalize",
    "email_normalize_all",
    "email_split",
    "encapsulate_email",
    "formataddr",
    "html2plaintext",
    "html_escape",
    "html_normalize",
    "html_sanitize",
    "is_html_empty",
    "parse_contact_from_email",
    "plaintext2html",
    "single_email_re",
]


# ----------------------------------------------------------
# Emails
# ----------------------------------------------------------


def generate_tracking_message_id(res_id):
    """Returns a string that can be used in the Message-ID RFC822 header field

    Used to track the replies related to a given object thanks to the "In-Reply-To"
    or "References" fields that Mail User Agents will set.
    """
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


# was mail_thread.decode_header()
def decode_message_header(message, header, separator=" "):
    return separator.join(h for h in message.get_all(header, []) if h)
