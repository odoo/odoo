# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountMove(models.Model):

    _inherit = 'account.move'

    withholding_ids = fields.One2many('account.move.line', 'move_id', string='Withholdings',
        copy=False, readonly=True, domain=[('tax_line_id', '!=', False)],
        states={'draft': [('readonly', False)]})


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    withholding_ids = fields.One2many(related='move_id.withholding_ids', readonly=False,)

    def _prepare_withholding_line_vals(self, tax, tax_amount, tax_base_amount, name):
        self.ensure_one()
        # TODO we should implemente many repartiotion lines functionality
        if self.partner_type == 'customer' and self.payment_type == 'inbound' or self.partner_type == 'supplier' and self.payment_type == 'outbound':
            tax_repartition_line = self.env['account.tax.repartition.line'].search([('repartition_type', '=', 'tax'), ('invoice_tax_id', '=', tax.id)], limit=1)
        else:
            tax_repartition_line = self.env['account.tax.repartition.line'].search([('repartition_type', '=', 'tax'), ('refund_tax_id', '=', tax.id)], limit=1)
        tax_amount = self.currency_id._convert(tax_amount, self.company_id.currency_id, self.company_id, self.date)
        currency_id = self.currency_id.id
        return {
            'name': name,
            'account_id': tax_repartition_line.account_id.id,
            'tax_base_amount': tax_base_amount,
            'tax_repartition_line_id': tax_repartition_line.id,
            'partner_id': self.partner_id.id,
            'currency_id': currency_id,
            'debit': tax_amount > 0.0 and tax_amount or 0.0,
            'credit': tax_amount < 0.0 and -tax_amount or 0.0,
        }

    # @api.model_create_multi
    # def create(self, vals_list):
    #     withholdings_vals_list = []

    #     for vals in vals_list:

    #         # Hack to add a custom write-off line.
    #         withholdings_vals_list.append(vals.pop('withholding_vals', None))
    #     payments = super().create(vals_list)

    #     for i, pay in enumerate(payments):
    #         withholdings_vals = withholdings_vals_list[i]

    #         line_ids = []

    #         if 'line_ids' not in vals_list[i]:
    #             for withholding_vals in withholdings_vals:
    #                 # TODO all line values are returned, if used, we should only get withholding line
    #                 line_ids += [(0, 0, line_vals) for line_vals in pay._prepare_move_line_default_vals(write_off_line_vals=withholding_vals)]

    #         pay.move_id.write({'line_ids': line_ids})

    #     return payments
