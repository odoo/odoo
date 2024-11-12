from odoo import fields, models


class UomUom(models.Model):
    _inherit = 'uom.uom'

    l10n_es_edi_facturae_uom_code = fields.Selection(
        selection=[
            ('01', 'Units'),
            ('02', 'Hours'),
            ('03', 'Kilograms'),
            ('04', 'Liters'),
            ('05', 'Other'),
            ('06', 'Boxes'),
            ('07', 'Trays, one layer no cover, plastic'),
            ('08', 'Barrels'),
            ('09', 'Jerricans, cylindrical'),
            ('10', 'Bags'),
            ('11', 'Carboys, non-protected'),
            ('12', 'Bottles, non-protected, cylindrical'),
            ('13', 'Canisters'),
            ('14', 'Tetra Briks'),
            ('15', 'Centiliters'),
            ('16', 'Centimeters'),
            ('17', 'Bins'),
            ('18', 'Dozens'),
            ('19', 'Cases'),
            ('20', 'Demijohns, non-protected'),
            ('21', 'Grams'),
            ('22', 'Kilometers'),
            ('23', 'Cans, rectangular'),
            ('24', 'Bunches'),
            ('25', 'Meters'),
            ('26', 'Millimeters'),
            ('27', '6-Packs'),
            ('28', 'Packages'),
            ('29', 'Portions'),
            ('30', 'Rolls'),
            ('31', 'Envelopes'),
            ('32', 'Tubs'),
            ('33', 'Cubic meter'),
            ('34', 'Second'),
            ('35', 'Watt'),
            ('36', 'Kilowatt-hour')
    ], string='Spanish EDI Units', default="05", required=True)
