# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models, SUPERUSER_ID


class SaleAdvancePaymentInv(models.TransientModel):
    _name = 'sale.advance.payment.inv'
    _description = "Sales Advance Payment Invoice"
    _inherit = ['account.advance.payment.wizard']

    amount_to_invoice = fields.Monetary(help="The amount to invoice = Sale Order Total - Amount already invoiced.")
    order_ids = fields.Many2many('sale.order')

    consolidated_billing = fields.Boolean(
        string="Consolidated Billing", default=True,
        help="Create one invoice for all orders related to same customer and same invoicing address",
    )

    def view_draft_invoices(self):
        res = super().view_draft_invoices()
        res['domain'].append(('line_ids.sale_line_ids.order_id', 'in', self.order_ids.ids))
        return res

    def _needs_to_group_on_invoice(self):
        return not self.consolidated_billing

    def _get_payment_term_account_type(self):
        return 'asset_receivable'

    def _get_product_account_internal_group(self):
        return 'income'

    def _create_down_payment_invoice(self):
        invoice = super()._create_down_payment_invoice()
        poster = self.env.user._is_internal() and self.env.user.id or SUPERUSER_ID
        invoice.with_user(poster).message_post_with_source(
            'mail.message_origin_link',
            render_values={'self': invoice, 'origin': self.order_ids},
            subtype_xmlid='mail.mt_note',
        )
        title = _("Down payment invoice")
        self.order_ids.with_user(poster).message_post(
            body=_("%s has been created", invoice._get_html_link(title=title)),
        )
        return invoice
