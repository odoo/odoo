# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, SUPERUSER_ID


class PurchaseAdvancePaymentWizard(models.TransientModel):
    _name = 'purchase.advance.payment.wizard'
    _description = "Purchase Advance Payment Bill"
    _inherit = ["account.advance.payment.wizard"]

    advance_payment_method = fields.Selection(
        string="Create Bill",
        help="A standard vendor bill is created with all the order lines ready for billing, "
             "according to their bill policy (based on ordered or received quantity).",
    )

    amount = fields.Float(help="The percentage of amount billed in advance.")
    fixed_amount = fields.Monetary(help="The fixed amount billed in advance.")

    amount_to_invoice = fields.Monetary(string="Amount to be billed", help="The amount to be billed = Purchase Order Total - Amount already billed.")
    amount_invoiced = fields.Monetary(string="Amount already billed")
    order_ids = fields.Many2many('purchase.order')

    def view_draft_invoices(self):
        res = super().view_draft_invoices()
        res['name'] = _('Draft Bills')
        res['domain'].append(('line_ids.purchase_order_id.id', 'in', self.order_ids.ids))
        return res

    def _get_payment_term_account_type(self):
        return 'liability_payable'

    def _get_product_account_internal_group(self):
        return 'expense'

    def _create_down_payment_invoice(self):
        invoice = super()._create_down_payment_invoice()
        poster = self.env.user._is_internal() and self.env.user.id or SUPERUSER_ID
        title = _("Down payment vendor bill")
        self.order_ids.with_user(poster).message_post(
            body=_("%s has been created", invoice._get_html_link(title=title)),
        )
        return invoice
