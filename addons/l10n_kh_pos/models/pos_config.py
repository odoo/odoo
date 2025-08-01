# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    khmer_receipt = fields.Boolean(string="Enable Khmer Receipt Format")

    @api.constrains("khmer_receipt")
    def _check_khmer_receipt(self):
        for config in self:
            if config.khmer_receipt and config.company_id.country_id.code != 'KH':
                raise ValidationError(_("Khmer Receipt Format is only available for companies in Cambodia."))
            if config.khmer_receipt and not self.env.ref('base.KHR').active:
                raise ValidationError(_("Khmer Receipt Format requires Khmer Riel to be active."))
