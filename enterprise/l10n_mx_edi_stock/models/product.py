from odoo import models, fields


class ProductCode(models.Model):
    _inherit = 'product.unspsc.code'

    l10n_mx_edi_hazardous_material = fields.Selection(
        selection=[
            ('1', 'Hazardous'),
            ('0,1', 'Maybe Hazardous'),
        ],
        string='(MX) Is Hazardous Material',
    )
