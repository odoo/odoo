# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import is_html_empty, lazy
from odoo.addons import web_editor, mail, http_routing


class IrQweb(web_editor.IrQweb, http_routing.IrQweb, mail.IrQweb):

    def _prepare_frontend_environment(self, values):
        """ Returns ir.qweb with context and update values with portal specific
            value (required to render portal layout template)
        """
        irQweb = super()._prepare_frontend_environment(values)
        values.update(
            is_html_empty=is_html_empty,
            frontend_languages=lazy(lambda: irQweb.env['res.lang']._get_frontend())
        )
        for key in irQweb.env.context:
            if key not in values:
                values[key] = irQweb.env.context[key]

        return irQweb
