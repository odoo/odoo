import lxml.html.clean
import re

from importlib.metadata import version

from odoo.tools import parse_version


def patch_module():
    # between these versions having a couple data urls in a style attribute
    # or style node removes the attribute or node erroneously
    if parse_version("4.6.0") <= parse_version(version('lxml')) < parse_version("5.2.0"):
        lxml.html.clean._find_image_dataurls = re.compile(r'data:image/(.+?);base64,').findall
