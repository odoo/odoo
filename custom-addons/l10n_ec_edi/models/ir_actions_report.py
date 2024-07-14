# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        # Overridden so that the print withhold action raises an error if it is not a withhold
        if self._get_report(report_ref).report_name == 'l10n_ec_edi.report_withhold':
            not_wh_moves = self.env['account.move'].browse(res_ids).filtered(lambda m: not m.l10n_ec_withhold_type)
            if not_wh_moves:
                raise UserError(_("This document is not a withhold. "))
        if self._get_report(report_ref).report_name in ['account.report_invoice_with_payments', 'account.report_invoice']:
            wh_moves = self.env['account.move'].browse(res_ids).filtered(lambda m: m.l10n_ec_withhold_type)
            if wh_moves:
                raise UserError(_("This document is a withhold. Use the 'Withholds' button."))

        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
