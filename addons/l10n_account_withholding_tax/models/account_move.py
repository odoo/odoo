from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # is_withhold_entry = fields.Boolean(string="Is Withhold Entry")
    l10n_withholding_ref_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Withhold Ref Move",
        readonly=True,
        index='btree_not_null',
        copy=False,
        help="Reference move for withholding entry",
    )
    l10n_in_withhold_move_ids = fields.One2many(
        'account.move', 'l10n_withholding_ref_move_id',
        string="Indian TDS Entries"
    )

    def _compute_payments_widget_reconciled_info(self):
        """Add withhold field in the reconciled vals to be able to show the payment method in the invoice."""
        super()._compute_payments_widget_reconciled_info()
        for move in self:
            if move.invoice_payments_widget:
                print("\n\n----------------------------")
                print(move.invoice_payments_widget)
                print("----------------------------\n\n")
                if move.state == 'posted' and move.is_invoice(include_receipts=True):
                    reconciled_partials = move._get_all_reconciled_invoice_partials()
                    for i, reconciled_partial in enumerate(reconciled_partials):
                        print("======")
                        print(i)
                        print(reconciled_partial)
                        print(reconciled_partial['aml'])
                        print("======")
                        # counterpart_line = reconciled_partial['aml']
                        # pos_payment = counterpart_line.move_id.sudo().pos_payment_ids[:1]
                        # move.invoice_payments_widget['content'][i].update({
                        #     'pos_payment_name': pos_payment.payment_method_id.name,
                        # })

    def _get_withhold_account_by_sum(self):
        print("======= Withhold Data =======")
        self.ensure_one()
        withhold_data = {}
        for line in self.invoice_line_ids:
            if line.account_id.withhold_tax_ids:
                withhold_data[line.account_id.id] = line.price_subtotal
        for line in self.l10n_in_withhold_move_ids.line_ids:
            print(line.account_id)
            if line.account_id.id in withhold_data:
                withhold_data[line.account_id.id] -= line.price_subtotal
        print(withhold_data)
        print("=============================")
        return withhold_data

    def action_create_withholding(self):
        print(self)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_withhold_line = fields.Boolean(
        string="Is Withhold Line",
        compute='_compute_is_withhold_line'
    )

    def _compute_is_withhold_line(self):
        for line in self:
            print("================", line, "================")
            line.is_withhold_line = bool(line.tax_ids.filtered('is_withhold_tax'))