# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

UNALTERABLE_COUNTRIES = ['DE']


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.multi
    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        # fiscalyear_lock_date can't be set to a prior date
        if 'fiscalyear_lock_date' in vals or 'period_lock_date' in vals:
            self._check_lock_dates(vals)
        return res

    def _is_vat_german(self):
        return self.vat and self.vat.startswith('DE') and len(self.vat) == 13

    def _is_accounting_gobd_unalterable(self):
        if not self.vat and not self.country_id:
            return False
        return self.country_id and self.country_id.code in UNALTERABLE_COUNTRIES or self._is_vat_german()
