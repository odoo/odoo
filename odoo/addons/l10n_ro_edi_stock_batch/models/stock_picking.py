from odoo import api, models


class Picking(models.Model):
    _inherit = 'stock.picking'

    @api.depends('batch_id', 'company_id')
    def _compute_l10n_ro_edi_stock_enable(self):
        # OVERRIDES 'l10n_ro_edi_stock'
        for picking in self:
            picking.l10n_ro_edi_stock_enable = not picking.batch_id and picking.company_id.country_id.code == 'RO'

    @api.model
    def _l10n_ro_edi_stock_validate_carrier_filter(self, picking):
        # OVERRIDE l10n_ro_edi_stock

        # Override for when the batch picking calls this function to validate the carriers
        validate_carrier = self.env.context.get('l10n_ro_edi_stock_validate_carrier', False)

        return picking.company_id.account_fiscal_country_id.code == 'RO' and (picking.l10n_ro_edi_stock_enable or validate_carrier)
