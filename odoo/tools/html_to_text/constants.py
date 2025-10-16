# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

SURROUNDING_WHITESPACE_REGEX = re.compile(r"^(\s*)(.*?)(\s*)$", flags=re.DOTALL)

LINK_TAG_PREFIX = r"LINK#"
UUID_REGEX = r"[0-9a-fA-F]{8}([0-9a-fA-F]{4}){3}[0-9a-fA-F]{12}"  # adapted from pyparsing to remove "-"
LINK_TAG_REGEX = LINK_TAG_PREFIX + UUID_REGEX

INDENT = " " * 3
BEFORE_EOL = ""
