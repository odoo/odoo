from odoo import api, fields, models
from odoo.addons.l10n_gr_edi.models.preferred_classification import (
    MEASUREMENT_UNIT_SELECTION,
)
from odoo.addons.l10n_gr_edi.utils import street_split


class StockMove(models.Model):
    _inherit = 'stock.move'

    l10n_gr_edi_measurement_unit = fields.Selection(
        selection=MEASUREMENT_UNIT_SELECTION,
        string="myDATA Unit of Measure",
        compute='_compute_l10n_gr_edi_measurement_unit',
        store='True',
    )

    @api.depends('picking_id.is_greek_company', 'uom_id')
    def _compute_l10n_gr_edi_measurement_unit(self):
        uom_map = {name: code for code, name in MEASUREMENT_UNIT_SELECTION}
        for move in self:
            if self.company_id.account_fiscal_country_id.code == 'GR' and move.uom_id:
                move.l10n_gr_edi_measurement_unit = uom_map.get(move.uom_id.with_context(lang='en_US').name)
            else:
                move.l10n_gr_edi_measurement_unit = False

    def _get_new_picking_values(self):
        # EXTENDS
        values = super()._get_new_picking_values()
        if self.company_id.account_fiscal_country_id.code != 'GR':
            return values
        street_detail_loading = street_split(self.company_id.street)
        street_detail_delivery = street_split(self.partner_id.street)
        return {
            **values,
            'l10n_gr_edi_loading_address_street': street_detail_loading.get('street_name'),
            'l10n_gr_edi_loading_address_number': street_detail_loading.get('street_number'),
            'l10n_gr_edi_loading_address_zip': self.company_id.zip,
            'l10n_gr_edi_loading_address_city': self.company_id.city,
            'l10n_gr_edi_delivery_address_street': street_detail_delivery.get('street_name'),
            'l10n_gr_edi_delivery_address_number': street_detail_delivery.get('street_number'),
            'l10n_gr_edi_delivery_address_zip': self.partner_id.zip,
            'l10n_gr_edi_delivery_address_city': self.partner_id.city,
        }
