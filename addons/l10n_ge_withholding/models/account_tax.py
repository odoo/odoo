from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ge_wht_category_ids = fields.Many2many(
        comodel_name='l10n_ge.wht.category',
        string="Withholding Tax Categories",
        help="Income recipient categories this withholding tax applies to. When a contact has categories,"
        " only taxes sharing one of them are offered on its bills and payments.",
    )

    @api.model
    def _prepare_base_line_tax_repartition_grouping_key(self, base_line, base_line_grouping_key, tax_data, tax_rep_data):
        """Keep the zero Georgian withholding tax lines: a fully exempt withholding is still declared on the return."""
        # EXTENDS account
        grouping_key = super()._prepare_base_line_tax_repartition_grouping_key(base_line, base_line_grouping_key, tax_data, tax_rep_data)
        tax = tax_data["tax"]
        if tax.country_code == "GE" and tax.is_withholding_tax:
            grouping_key["__keep_zero_line"] = True
        return grouping_key
