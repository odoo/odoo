# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .simple import simple
from .rml import rml, rml2html, rml2txt, odt2odt , html2html, makohtml2html
from .render import render

try:
    from PIL import Image
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)
    _logger.warning('Python Imaging not installed, you can use only .JPG pictures !')
