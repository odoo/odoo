# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    paperformat_id = fields.Many2one(related="company_id.paperformat_id", string='Paper format *')

    def edit_external_header(self):
        return self.company_id.edit_external_header()

    def edit_external_footer(self):
        return self.company_id.edit_external_footer()

    def edit_internal_header(self):
        return self.company_id.edit_internal_header()
