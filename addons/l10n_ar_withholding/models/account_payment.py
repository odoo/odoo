# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    withholding_ids = fields.One2many(related='move_id.withholding_ids', readonly=False,)

    def _synchronize_to_moves(self, changed_fields):
        ''' If we change a payment with witholdings, delete all withholding lines as the synchronization mechanism is not
        implemented yet
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        for pay in self.with_context(
                skip_account_move_synchronization=True, check_move_validity=False, skip_invoice_sync=True, dynamic_unlink=True):
            pay.line_ids.filtered('tax_line_id').unlink()
            pay.line_ids.filtered('tax_ids').tax_ids = False
        res = super()._synchronize_to_moves(changed_fields)
        return res

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

    # TODO ver si necesitamos este metodo o no, por ahora la linea la esta creando odoo automaticamente pero deberiamos
    # chequear cuando usa repartition refund vs invoice
    # def _prepare_withholding_line_vals(self, tax, tax_amount, tax_base_amount, name):
    #     self.ensure_one()
    #     # if self.partner_type == 'customer' and self.payment_type == 'inbound' or self.partner_type == 'supplier' and self.payment_type == 'outbound':
    #     #     tax_repartition_line = self.env['account.tax.repartition.line'].search(
    #     #         [('document_type', '=', 'invoice'), ('repartition_type', '=', 'tax'), ('tax_id', '=', tax.id)], limit=1)
    #     # else:
    #     #     tax_repartition_line = self.env['account.tax.repartition.line'].search(
    #     #         [('document_type', '=', 'refund'), ('repartition_type', '=', 'tax'), ('tax_id', '=', tax.id)], limit=1)
    #     tax_amount = self.currency_id._convert(tax_amount, self.company_id.currency_id, self.company_id, self.date)
    #     tax_line.amount_currency
    #     return {
    #         # TODO ver de borrar, los campos calculados ahora los esta calculando odoo automaticamente con aml._compute_all_tax
    #         # 'name': name,
    #         # 'display_type': 'tax',
    #         # 'tax_repartition_line_id': tax_repartition_line.id,
    #         # 'account_id': tax_repartition_line.account_id.id,
    #         'tax_base_amount': tax_base_amount,
    #         'partner_id': self.partner_id.id,
    #         'currency_id': currency_id,
    #         'debit': tax_amount > 0.0 and tax_amount or 0.0,
    #         'credit': tax_amount < 0.0 and -tax_amount or 0.0,
    #     }
