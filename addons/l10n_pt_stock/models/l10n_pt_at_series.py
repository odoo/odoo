from odoo import _, fields, models
from odoo.exceptions import UserError

AT_SERIES_MOVEMENT_DOCUMENT_TYPES = [
    ('outgoing', 'Transport Guide (GT)'),
    ('internal', 'Internal Transport Document (GA)'),
    ('incoming', 'Return Note (GD)'),
]


class L10nPtATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    document_type = fields.Selection(
        selection_add=AT_SERIES_MOVEMENT_DOCUMENT_TYPES,
        ondelete={'outgoing': 'cascade', 'internal': 'cascade', 'incoming': 'cascade'},
    )

    def _has_stock_pickings(self):
        self.ensure_one()
        return self.env['stock.picking'].search_count([
            ('l10n_pt_at_series_id', '=', self.id),
            ('state', 'in', ('done', 'cancel')),
        ], limit=1)

    def write(self, vals):
        if any(f in vals for f in ('name', 'training_series', 'document_type', 'prefix', 'at_code')):
            for at_series in self:
                if at_series._has_stock_pickings():
                    raise UserError(_("You cannot change the name, training status, type, prefix or AT code of a series that has already been used."))
        return super().write(vals)
