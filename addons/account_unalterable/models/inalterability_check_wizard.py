# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountInalterabilityCheckWizard(models.TransientModel):
    _name = 'account.inalterability.check'
    _description = 'Data Inalterability Check'

    @api.multi
    def check_account_move_hash_integrity(self):
        self.env['account.move']._check_hash_integrity()
