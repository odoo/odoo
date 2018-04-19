# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


UNALTERABLE_COUNTRIES = ['FR', 'MF', 'MQ', 'NC', 'PF', 'RE', 'GF', 'GP', 'TF']


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.multi
    def _is_accounting_unalterable(self):
        self.ensure_one()
        if self.country_id and self.country_id.code in UNALTERABLE_COUNTRIES:
            return True
        if self.vat and len(self.vat) > 2 and self.vat[:2].upper() in UNALTERABLE_COUNTRIES:
            return True
        return False
