from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nPtATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    def _has_pos_orders(self):
        self.ensure_one()
        return self.env['pos.order'].search_count([
            ('l10n_pt_at_series_id', '=', self.id),
            ('state', '!=', 'draft'),
        ], limit=1)

    def write(self, vals):
        if 'name' in vals or 'training_series' in vals:
            for at_series in self:
                if at_series._has_pos_orders():
                    raise UserError(_("You cannot change the name or training status of a series that has already been used."))
        return super().write(vals)


class L10nPtPosATSeriesLine(models.Model):
    _inherit = "l10n_pt.at.series.line"

    type = fields.Selection(
        selection_add=[('pos_order', 'Invoice/Receipt (FR)')],
        ondelete={'pos_order': 'cascade'},
        help=" * Invoice (FT): Series for Customer Invoices.\n"
             " * Simplified Invoice (FS): Series for Sales Receipts.\n"
             " * Invoice/Receipt (FR): Series for PoS Orders.",
    )

    def write(self, vals):
        if 'type' in vals or 'prefix' in vals or 'at_code' in vals:
            for at_series_line in self:
                if at_series_line.at_series_id._has_pos_orders():
                    raise UserError(_("You cannot change the type, prefix or AT code of a series that has already been used."))
        return super().write(vals)
