# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    country_code = fields.Char(related="company_id.account_fiscal_country_id.code")

    @api.constrains("scheduled_date", "date_done")
    def _check_backdate_allowed(self):
        for picking in self:
            if picking._is_date_in_lock_period():
                raise ValidationError(self.env._("You cannot modify the scheduled date of this operation because it falls within a locked fiscal period."))

    def _compute_is_date_editable(self):
        super()._compute_is_date_editable()
        for picking in self:
            if picking.is_date_editable and picking.state in ['done', 'cancel'] and picking.ids:
                picking.is_date_editable = not picking._is_date_in_lock_period()

    def _is_date_in_lock_period(self):
        self.ensure_one()
        lock = self.company_id._get_lock_date_violations(self.scheduled_date.date(), fiscalyear=True)
        if self.date_done:
            lock += self.company_id._get_lock_date_violations(self.date_done.date(), fiscalyear=True)
        return bool(lock)
