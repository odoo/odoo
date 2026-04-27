# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    def _get_nr_nacha_files(self):
        nr = super()._get_nr_nacha_files()
        nr += self.env['hr.payslip.run'].search_count([("nacha_effective_date", "=", self.date)])
        nr += self.env['hr.payslip'].search_count([("nacha_effective_date", "=", self.date)])
        return nr
