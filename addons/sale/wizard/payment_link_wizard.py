# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'
    _description = 'Generate Sales Payment Link'

    amount_paid = fields.Monetary(string="Already Paid", readonly=True)
    prepayment_amount = fields.Monetary(string="Prepayment Amount", currency_field='currency_id')
    confirmation_message = fields.Char(
        string="Confirmation Message", compute='_compute_confirmation_message'
    )

    @api.depends('amount')
    def _compute_confirmation_message(self):
        self.confirmation_message = False
        for wizard in self.filtered(lambda w: w.res_model == 'sale.order'):
            sale_order = wizard.env['sale.order'].browse(wizard.res_id)
            if sale_order.state in ('draft', 'sent') and sale_order.require_payment:
                wizard.confirmation_message = _("This payment will confirm the quotation.")

    @api.depends('res_model', 'res_id')
    def _compute_warning_message(self):
        sale_wizards = self.env['payment.link.wizard']
        for wizard in self.filtered(lambda w: w.res_model == 'sale.order'):
            sale_order = wizard.env['sale.order'].browse(wizard.res_id)
            if sale_order.state in ('draft', 'sent') and wizard.amount < wizard.prepayment_amount:
                wizard.warning_message = _("The amount must be greater than the prepayment amount.")
                sale_wizards |= wizard  # Prevent the super call from clearing the warning message.
            if sale_order.is_expired:
                wizard.warning_message = _("The sale order has expired.")
                sale_wizards |= wizard
        super(PaymentLinkWizard, self - sale_wizards)._compute_warning_message()

    def _prepare_url(self, base_url, related_document):
        """ Override of `payment` to use the portal page URL of sales orders. """
        if self.res_model == 'sale.order':
            return f'{base_url}{related_document.get_portal_url()}'
        else:
            return super()._prepare_url(base_url, related_document)

    def _prepare_query_params(self, *args):
        """ Override of `payment` to add SO-related values to the query params. """
        if self.res_model == 'sale.order':
            return {'payment_amount': self.amount}
        else:
            return super()._prepare_query_params(*args)
