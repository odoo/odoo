# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nCoEdiPaymentMeans(models.Model):
    _name = 'l10n_co_edi.payment.means'
    _description = 'DIAN Payment Means Code'
    _order = 'code'

    code = fields.Char(
        string='Code',
        required=True,
        help='DIAN payment means code per UN/CEFACT 4461.',
    )
    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )

    _unique_code = models.Constraint(
        'UNIQUE(code)',
        'Payment means code must be unique.',
    )
