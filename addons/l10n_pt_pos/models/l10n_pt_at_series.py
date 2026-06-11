from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nPtATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    document_type = fields.Selection(
        selection_add=[('pos_order', 'Invoice/Receipt (FR)')],
        ondelete={'pos_order': 'cascade'},
    )

    def _has_pos_orders(self):
        self.ensure_one()
        return self.env['pos.order'].search_count([
            ('l10n_pt_at_series_id', '=', self.id),
            ('state', '!=', 'draft'),
        ], limit=1)

    def write(self, vals):
        if any(f in vals for f in ('name', 'training_series', 'document_type', 'prefix', 'at_code')):
            for at_series in self:
                if at_series._has_pos_orders():
                    raise UserError(_("You cannot change the name, training status, type, prefix or AT code of a series that has already been used."))
        return super().write(vals)
