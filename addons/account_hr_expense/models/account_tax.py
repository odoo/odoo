from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    hr_expense_ids = fields.Many2many(
        comodel_name='hr.expense',
        relation='expense_tax',
        column1='tax_id',
        column2='expense_id',
        copy=False,
        readonly=True,
    )

    @api.depends('hr_expense_ids')
    def _compute_is_used(self):
        super()._compute_is_used()
        self.sudo().search([
            ('id', 'in', self.filtered(lambda t: not t.is_used).ids),
            ('hr_expense_ids', '!=', False),
        ]).is_used = True

    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        results['expense_id'] = self._get_base_line_field_value_from_record(record, 'expense_id', kwargs, self.env['hr.expense'])
        return results

    def _prepare_tax_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_tax_line_for_taxes_computation(record, **kwargs)
        results['expense_id'] = self._get_base_line_field_value_from_record(record, 'expense_id', kwargs, self.env['hr.expense'])
        return results

    def _prepare_base_line_grouping_key(self, base_line):
        # EXTENDS 'account'
        results = super()._prepare_base_line_grouping_key(base_line)
        results['expense_id'] = base_line['expense_id'].id
        return results

    def _prepare_tax_line_repartition_grouping_key(self, tax_line):
        # EXTENDS 'account'
        results = super()._prepare_tax_line_repartition_grouping_key(tax_line)
        results['expense_id'] = tax_line['expense_id'].id
        return results
