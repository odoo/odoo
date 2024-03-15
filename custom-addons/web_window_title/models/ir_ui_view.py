# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class View(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def _render_template(self, template, values=None):
        if template in ['web.login', 'web.webclient_bootstrap']:
            if not values:
                values = {}
            values["title"] = self.env['ir.config_parameter'].sudo().get_param("web.base.title", "")
        return super(View, self)._render_template(template, values)
