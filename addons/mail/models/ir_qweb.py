# -*- coding: utf-8 -*-
from odoo import models

class QWebCodeFound(Exception):
    """
    Exception raised when a qweb compilation encounter dynamic content if the
    option `raise_on_code` is True.
    """

class IrQweb(models.AbstractModel):
    _inherit = 'ir.qweb'

    def _get_template_cache_keys(self):
        return super()._get_template_cache_keys() + ['raise_on_code']

    def _compile_directives(self, el, options, indent):
        if options.get('raise_on_code'):
            raise QWebCodeFound()
        return super()._compile_directives(el, options, indent)
