# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductUoM(models.Model):
    _inherit = 'uom.uom'

    l10n_hu_edi_code = fields.Selection(
        selection=[
            ('PIECE', 'Piece'),
            ('KILOGRAM', 'Kilogram'),
            ('TON', 'Ton'),
            ('KWH', 'Kilowatt hour'),
            ('DAY', 'Day'),
            ('HOUR', 'Hour'),
            ('MINUTE', 'Minute'),
            ('MONTH', 'Month'),
            ('LITRE', 'Litre'),
            ('KILOMETER', 'Kilometer'),
            ('CUBIC_METER', 'Cubic meter'),
            ('METER', 'Meter'),
            ('LINEAR_METER', 'Linear meter'),
            ('CARTON', 'Carton'),
            ('PACK', 'Package'),
        ],
        string='NAV UoM code',
        help='Choose the corresponding code, or leave blank if none correspond.',
    )
