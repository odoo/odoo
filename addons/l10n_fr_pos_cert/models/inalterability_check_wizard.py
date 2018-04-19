# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountInalterabilityCheckWizard(models.TransientModel):
    _inherit = 'account.inalterability.check'

    @api.multi
    def check_pos_order_hash_integrity(self):
        self.env['pos.order']._check_hash_integrity()
