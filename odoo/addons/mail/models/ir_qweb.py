# -*- coding: utf-8 -*-
from odoo import models

class IrQweb(models.AbstractModel):
    """ Add ``raise_on_code`` option for qweb. When this option is activated
    then all directives are prohibited.
    """
    _inherit = 'ir.qweb'

    def _get_template_cache_keys(self):
        return super()._get_template_cache_keys() + ['raise_on_code']

    def _compile_directives(self, el, compile_context, indent):
        if compile_context.get('raise_on_code'):
            raise PermissionError("This rendering mode prohibits the use of directives.")
        return super()._compile_directives(el, compile_context, indent)
