# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import is_html_empty, lazy


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _prepare_environment(self, values):
        """ Returns ir.qweb with context and update values with portal specific
            value (required to render portal layout template)
        """
        irQweb = super()._prepare_environment(values)

        if not irQweb.env.context.get('minimal_qcontext'):
            values.update(
                is_html_empty=is_html_empty,
                frontend_languages=lazy(irQweb.env['res.lang']._get_frontend)
            )
            for key in irQweb.env.context:
                values.setdefault(key, irQweb.env.context[key])

        return irQweb
