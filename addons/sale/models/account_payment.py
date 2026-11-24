# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    sale_order_id = fields.Many2one(
        string="Sales Order",
        comodel_name="sale.order",
        readonly=True,
        copy=False,
        index="btree_not_null",
        check_company=True,
    )

    @api.depends("company_id", "sale_order_id")
    def _compute_available_journal_ids(self):
        """Override of `account` to offer the journals of the order's company, which may not be the
        active company."""
        order_payments = self.filtered("sale_order_id")
        super(AccountPayment, self - order_payments)._compute_available_journal_ids()
        for company, payments in order_payments.grouped("company_id").items():
            super(AccountPayment, payments.with_company(company))._compute_available_journal_ids()
