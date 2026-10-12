from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_sa.models.zatca_mixin import ADJUSTMENT_REASONS


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = 'pos.order'

    l10n_sa_reason = fields.Selection(string="ZATCA Reason", selection=ADJUSTMENT_REASONS)
    l10n_sa_reason_value = fields.Char(compute='_compute_l10n_sa_reason_value')

    def _get_l10n_sa_totals(self):
        self.ensure_one()
        return {
            'total_amount': self.amount_total,
            'total_tax': self.amount_tax,
        }

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.company_id.country_id.code == 'SA':
            mapped_reasons = self.mapped('l10n_sa_reason')
            if len(set(mapped_reasons)) > 1:
                raise UserError(_(
                    "You cannot create a consolidated invoice for POS orders with different"
                    " ZATCA refund reasons.",
                ))
            confirmation_datetime = self.date_order if len(self) == 1 else fields.Datetime.now()
            vals.update({
                'l10n_sa_confirmation_datetime': confirmation_datetime,
                'l10n_sa_reason': mapped_reasons[0] if mapped_reasons else False,
            })
        return vals

    @api.depends("l10n_sa_reason")
    def _compute_l10n_sa_reason_value(self):
        for record in self:
            record.l10n_sa_reason_value = dict(ADJUSTMENT_REASONS).get(record.l10n_sa_reason)
