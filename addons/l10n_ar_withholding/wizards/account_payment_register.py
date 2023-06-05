# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError


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

    def _tax_compute_all_helper(self):
        self.ensure_one()
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100
        taxes_res = self.tax_id.compute_all(
            self.base_amount,
            currency=self.payment_register_id.currency_id,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
        )
        tax_amount = taxes_res['taxes'][0]['amount']
        tax_account_id = taxes_res['taxes'][0]['account_id']
        tax_repartition_line_id = taxes_res['taxes'][0]['tax_repartition_line_id']
        return tax_amount, tax_account_id, tax_repartition_line_id

    @api.depends('tax_id', 'base_amount')
    def _compute_amount(self):
        for line in self:
            if not line.tax_id:
                line.amount = 0.0
            else:
                line.amount, dummy, dummy = self._tax_compute_all_helper()


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

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['amount'] = self.net_amount
        conversion_rate = self.env['res.currency']._get_conversion_rate(
            self.currency_id,
            self.company_id.currency_id,
            self.company_id,
            self.payment_date,
        )
        for line in self.withholding_ids:
            if line.name == '/':
                raise UserError(_('Please enter withholding number for tax %s' % line.tax_id.name))

            dummy, account_id, tax_repartition_line_id = line._tax_compute_all_helper()

            balance = self.company_currency_id.round(line.amount * conversion_rate)
            payment_vals['write_off_line_vals'].append({
                'name': line.tax_id.name,
                'account_id': account_id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': line.amount,
                'balance': balance,
                'tax_base_amount': line.base_amount,
                'tax_repartition_line_id': tax_repartition_line_id,
            })
        return payment_vals
