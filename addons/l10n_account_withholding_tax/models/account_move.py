from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

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

    def _get_all_reconciled_invoice_partials(self):
        """ Override to add more data to be used in the payments widget. """
        reconciled_partials = super()._get_all_reconciled_invoice_partials()
        for i, reconciled_partial in enumerate(reconciled_partials):
            if reconciled_partial['aml'].move_id.l10n_withholding_ref_move_id:
                reconciled_partials[i]['is_withhold_line'] = True
            else:
                reconciled_partials[i]['is_withhold_line'] = False
        return reconciled_partials

    def _compute_payments_widget_reconciled_info(self):
        """Add withhold field in the reconciled vals to be able to show the payment method in the invoice."""
        super()._compute_payments_widget_reconciled_info()
        for move in self:
            if move.invoice_payments_widget:
                if move.state == 'posted' and move.is_invoice(include_receipts=True):
                    reconciled_partials = move._get_all_reconciled_invoice_partials()
                    for i, reconciled_partial in enumerate(reconciled_partials):
                        if reconciled_partial['aml'].is_withhold_line:
                            move.invoice_payments_widget['content'][i].update({
                                'is_withhold_line': True,
                            })
                        else:
                            move.invoice_payments_widget['content'][i].update({
                                'is_withhold_line': False,
                            })

    def _get_withhold_account_by_sum(self):
        withhold_data = {}
        for line in self.invoice_line_ids:
            if line.account_id.withhold_tax_ids:
                withhold_data[line.account_id] = line.price_subtotal
        for line in self.l10n_in_withhold_move_ids.line_ids:
            if line.account_id in withhold_data:
                withhold_data[line.account_id] -= line.price_subtotal
        return withhold_data


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_withhold_line = fields.Boolean(
        string="Is Withhold Line",
    )
