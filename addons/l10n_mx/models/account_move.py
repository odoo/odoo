# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_report_base_filename(self):
        self.ensure_one()
        if (self.company_id.country_id and self.company_id.country_id.code) == 'MX':
            if not self.is_invoice(include_receipts=True):
                raise UserError(_("Only invoices can be printed."))
            return self._get_move_display_name()
        return super()._get_report_base_filename()
