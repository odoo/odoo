from odoo import api, fields, models
from odoo.addons.l10n_gr_edi_delivery_note.utils import street_split

MEASUREMENT_UNIT_SELECTION = [
    ('1', "Units"),
    ('2', "kg"),
    ('3', "L"),
    ('4', "m"),
    ('5', "m²"),
    ('6', "m³"),
]


class StockMove(models.Model):
    _inherit = 'stock.move'

    l10n_gr_edi_measurement_unit = fields.Selection(
        selection=MEASUREMENT_UNIT_SELECTION,
        string="myDATA Unit of Measure",
        compute='_compute_l10n_gr_edi_measurement_unit',
        store=True,
    )

    @api.depends('picking_id.is_greek_company', 'product_uom')
    def _compute_l10n_gr_edi_measurement_unit(self):
        uom_map = {name: code for code, name in MEASUREMENT_UNIT_SELECTION}
        for move in self:
            if move.picking_id.is_greek_company and move.product_uom:
                move.l10n_gr_edi_measurement_unit = uom_map.get(move.product_uom.with_context(lang='en_US').name)
            else:
                move.l10n_gr_edi_measurement_unit = False

    def _get_new_picking_values(self):
        # EXTENDS 'stock'
        values = super()._get_new_picking_values()
        company = self.company_id[:1]
        if company.account_fiscal_country_id.code != 'GR':
            return values

        partner = self.env['res.partner'].browse(values.get('partner_id'))
        loading_partner = self.env['stock.picking']._l10n_gr_edi_get_loading_partner(self.picking_type_id[:1], company)
        loading_street = street_split(loading_partner.street)
        delivery_street = street_split(partner.street)
        return {
            **values,
            'l10n_gr_edi_loading_address_street': loading_street['street_name'],
            'l10n_gr_edi_loading_address_number': loading_street['street_number'],
            'l10n_gr_edi_loading_address_zip': loading_partner.zip,
            'l10n_gr_edi_loading_address_city': loading_partner.city,
            'l10n_gr_edi_delivery_address_street': delivery_street['street_name'],
            'l10n_gr_edi_delivery_address_number': delivery_street['street_number'],
            'l10n_gr_edi_delivery_address_zip': partner.zip,
            'l10n_gr_edi_delivery_address_city': partner.city,
        }
