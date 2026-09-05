from odoo import api, models


class Picking(models.Model):
    _inherit = 'stock.picking'

    @api.depends('batch_id', 'company_id', 'picking_type_code')
    def _compute_l10n_ro_edi_stock_enable(self):
        super()._compute_l10n_ro_edi_stock_enable()
        for picking in self:
            picking.l10n_ro_edi_stock_enable &= not picking.batch_id

    @api.model
    def _l10n_ro_edi_stock_validate_carrier_filter(self, picking):
        validate_carrier = self.env.context.get('l10n_ro_edi_stock_validate_carrier', False)
        return (
            super()._l10n_ro_edi_stock_validate_carrier_filter(picking)
            or (picking.company_id.account_fiscal_country_id.code == 'RO' and validate_carrier)
        )
