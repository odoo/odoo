from odoo import _, fields, models
from odoo.exceptions import UserError

AT_SERIES_SALES_DOCUMENT_TYPES = [
    ('quotation', 'Quotation (OR)'),
    ('sales_order', 'Sales Order (NE)'),
]


class L10nPtATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    def write(self, vals):
        if 'name' in vals or 'training_series' in vals:
            for at_series in self:
                if self.env['sale.order'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', '!=', 'draft'),
                ], limit=1):
                    raise UserError(_("You cannot change the name or training status of a series that has already been used."))
        return super().write(vals)


class L10nPtPosATSeriesLine(models.Model):
    _inherit = "l10n_pt.at.series.line"

    type = fields.Selection(
        selection_add=AT_SERIES_SALES_DOCUMENT_TYPES,
        ondelete={'quotation': 'cascade', 'sales_order': 'cascade'},
    )

    def write(self, vals):
        if 'type' in vals or 'prefix' in vals or 'at_code' in vals:
            for at_series_line in self:
                if self.env['sale.order'].search_count([
                    ('l10n_pt_at_series_line_id', '=', at_series_line.id),
                    ('state', '!=', 'draft'),
                ], limit=1):
                    raise UserError(_("You cannot change the type, prefix or AT code of a series that has already been used."))
        return super().write(vals)
