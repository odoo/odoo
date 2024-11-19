from odoo import _, fields, models


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    l10n_din5008_document_title = fields.Char(compute='_compute_l10n_din5008_document_title')

    def _compute_l10n_din5008_document_title(self):
        for sheet in self:
            sheet.l10n_din5008_document_title = _("Expenses Report")
