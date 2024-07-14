# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_in_exception = fields.Html("Exception")
    l10n_in_gst_return_period_id = fields.Many2one("l10n_in.gst.return.period", "GST Return Period")
    l10n_in_gstr2b_reconciliation_status = fields.Selection(selection=[
        ("pending", "Pending"),
        ("matched", "Fully Matched"),
        ("partially_matched", "Partially Matched"),
        ("exception", "Exception"),
        ("bills_not_in_gstr2", "Bills Not in GSTR-2"),
        ("gstr2_bills_not_in_odoo", "GSTR-2 Bills not in Odoo")],
        string="GSTR-2B Reconciliation",
        readonly=True,
        default="pending"
    )

    def _post(self, soft=True):
        for invoice in self:
            if invoice.l10n_in_gstr2b_reconciliation_status == "gstr2_bills_not_in_odoo":
                invoice.l10n_in_gstr2b_reconciliation_status = "pending"
        return super(AccountMove, self)._post(soft=soft)
