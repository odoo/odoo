# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    l10n_jp_closing_date = fields.Date(
        string="Closing Date",
        compute='_compute_l10n_jp_closing_date',
        store=True,
        help="Date from which this order is billed on the summary invoice of its customer.",
    )
    l10n_jp_missed_closing = fields.Boolean(
        string="Missed Closing",
        compute='_compute_l10n_jp_missed_closing',
        help="This order is still to invoice, although a closing date of its customer has passed since its own.",
    )

    @api.depends('date_order', 'partner_invoice_id.commercial_partner_id.l10n_jp_closing_day_ids')
    def _compute_l10n_jp_closing_date(self):
        for order in self:
            date_order = fields.Date.context_today(order, order.date_order)
            closing_dates = order.partner_invoice_id.commercial_partner_id._l10n_jp_get_closing_dates(date_order)
            order.l10n_jp_closing_date = min((date for date in closing_dates if date >= date_order), default=False)

    @api.depends('l10n_jp_closing_date', 'invoice_status')
    def _compute_l10n_jp_missed_closing(self):
        today = fields.Date.context_today(self)
        for order in self:
            closing_dates = order.partner_invoice_id.commercial_partner_id._l10n_jp_get_closing_dates(today)
            order.l10n_jp_missed_closing = order.invoice_status == 'to invoice' and order.l10n_jp_closing_date and any(
                order.l10n_jp_closing_date < date <= today for date in closing_dates
            )

    def _prepare_invoice(self):
        # EXTENDS 'sale'
        invoice_vals = super()._prepare_invoice()
        today = fields.Date.context_today(self)
        if self.l10n_jp_closing_date and self.l10n_jp_closing_date <= today:
            partner = self.partner_invoice_id.commercial_partner_id
            closing_dates = partner._l10n_jp_get_closing_dates(today)
            invoice_vals.update({
                'invoice_date': max(date for date in closing_dates if date <= today),
                # One summary invoice per billed customer, wherever its orders are delivered.
                'partner_shipping_id': self.partner_invoice_id.address_get(['delivery'])['delivery'],
            })
            if partner.l10n_jp_pay_at_next_closing:
                invoice_vals.update({
                    'invoice_payment_term_id': False,
                    'invoice_date_due': min(date for date in closing_dates if date > today),
                })
        return invoice_vals
