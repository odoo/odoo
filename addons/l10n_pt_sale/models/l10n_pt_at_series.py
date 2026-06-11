from odoo import _, fields, models
from odoo.exceptions import UserError

AT_SERIES_SALES_DOCUMENT_TYPES = [
    ('quotation', 'Quotation (OR)'),
    ('sales_order', 'Sales Order (NE)'),
]


class L10nPtATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    document_type = fields.Selection(
        selection_add=AT_SERIES_SALES_DOCUMENT_TYPES,
        ondelete={'quotation': 'cascade', 'sales_order': 'cascade'},
    )

    def write(self, vals):
        if any(f in vals for f in ('name', 'training_series', 'document_type', 'prefix', 'at_code')):
            for at_series in self:
                if self.env['sale.order'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', '!=', 'draft'),
                ], limit=1):
                    raise UserError(_("You cannot change the name, training status, type, prefix or AT code of a series that has already been used."))
        return super().write(vals)
