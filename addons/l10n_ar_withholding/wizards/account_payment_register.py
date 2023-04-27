# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountPaymentRegisterWithholding(models.TransientModel):
    _name = 'account.payment.register.withholding'
    _description = 'account.payment.register.withholding'

    payment_register_id = fields.Many2one('account.payment.register', required=True, ondelete='cascade',)
    currency_id = fields.Many2one(related='payment_register_id.currency_id')
    name = fields.Char(required=True)
    tax_id = fields.Many2one('account.tax', required=True,)
    base_amount = fields.Monetary(required=True, compute='_compute_base_amount', store=True, readonly=False)
    amount = fields.Monetary(required=True, compute='_compute_amount', store=True, readonly=False)

    @api.depends('tax_id', 'payment_register_id.line_ids', 'payment_register_id.amount')
    def _compute_base_amount(self):
        # TODO improve this method and send some funcionality to account.tax, this approach is for demo purpose
        # TODO also consider multicurrency use case
        base_lines = self.payment_register_id.line_ids.move_id.invoice_line_ids
        for rec in self:
            if not rec.tax_id:
                rec.base_amount = 0.0
            factor = rec.payment_register_id.amount / rec.payment_register_id.source_amount
            if self.payment_register_id.partner_type == 'supplier':
                tax_base_lines = base_lines.filtered(lambda x: rec.tax_id in x.product_id.l10n_ar_supplier_withholding_taxes_ids)
            else:
                tax_base_lines = base_lines
            if rec.tax_id.l10n_ar_withholding_amount_type == 'untaxed_amount':
                # TODO verificar que price_subtotal sea siempre sin impuestos
                rec.base_amount = factor * sum(tax_base_lines.mapped('price_subtotal'))
            elif rec.tax_id.l10n_ar_withholding_amount_type == 'tax_amount':
                # TODO implementar. debería ser el tax base amount the un tax de mismo group o algo así? o elegimos en otro campo de que tax?
                rec.base_amount = 0.0
            else:
                rec.base_amount = factor * sum(tax_base_lines.mapped('price_total'))

    @api.depends('tax_id', 'base_amount')
    def _compute_amount(self):
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount = line.tax_id._compute_amount(line.base_amount, line.base_amount)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    withholding_ids = fields.One2many(
        'account.payment.register.withholding', 'payment_register_id', string="Withholdings",
        compute='_compute_withholdings', readonly=False, store=True)
    total_amount = fields.Monetary(compute='_compute_total_amount', help="Total amount with withholdings")
    net_amount = fields.Monetary(compute='_compute_net_amount', help="Net amount after withholdings")

    @api.depends('line_ids')
    def _compute_withholdings(self):
        for rec in self.filtered(lambda x: x.partner_type == 'supplier'):
            taxes = rec.line_ids.move_id.invoice_line_ids.product_id.l10n_ar_supplier_withholding_taxes_ids.filtered(
                lambda y: y.company_id == self.company_id)
            fp = self.env['account.fiscal.position'].with_company(rec.company_id)._get_fiscal_position(rec.partner_id)
            taxes = fp.map_tax(taxes)
            rec.write({'withholding_ids': [(5, 0, 0)] + [(0, 0, {'tax_id': x.id, 'name': '/'}) for x in taxes]})

    @api.depends('withholding_ids.amount', 'amount')
    def _compute_net_amount(self):
        for rec in self:
            rec.net_amount = rec.amount - sum(rec.withholding_ids.mapped('amount'))

    # TODO implement on _create_payment_vals_from_wizard instead of here
    def _create_payments(self):
        payments = super()._create_payments()
        if self.withholding_ids:
            for payment in payments.with_context(check_move_validity=False):
                # TODO remove this hack when creating withholdings properly
                liquidity_lines, counterpart_lines, _ = payment._seek_for_lines()
                counterpart_lines.parent_state = 'draft'
                # TODO ver el caso de mas de una liquidity_lines
                rate = liquidity_lines.amount_currency / liquidity_lines.balance if liquidity_lines.balance else 1
                liquidity_lines.balance = self.net_amount / rate * (-1 if liquidity_lines.tax_tag_invert else 1)
                liquidity_lines.amount_currency = self.net_amount * (-1 if liquidity_lines.tax_tag_invert else 1)
                counterpart_lines.tax_ids = self.withholding_ids.mapped('tax_id')
                for line in self.withholding_ids:
                    tax_line = payment.line_ids.filtered(lambda x: x.tax_line_id == line.tax_id)
                    rate = tax_line.amount_currency / tax_line.balance if tax_line.balance else 1
                    tax_line.write({
                        'amount_currency': line.amount,
                        'tax_base_amount': line.base_amount / rate * (-1 if tax_line.tax_tag_invert else 1),
                        'balance': line.amount / rate,
                    })
                counterpart_lines.parent_state = 'posted'

        return payments
