# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import is_html_empty, lazy


class IrQWeb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _prepare_frontend_environment(self, values):
        """ Returns ir.qweb with context and update values with portal specific
            value (required to render portal layout template)
        """
        irQweb = super()._prepare_frontend_environment(values)
        values.update(
            is_html_empty=is_html_empty,
            languages=lazy(lambda: [lang for
                    lang in irQweb.env['res.lang'].get_available()
                    if lang[0] in irQweb.env['ir.http']._get_frontend_langs()])
        )
        for key in irQweb.env.context:
            if key not in values:
                values[key] = irQweb.env.context[key]

        return irQweb
