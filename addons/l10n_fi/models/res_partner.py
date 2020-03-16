# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResPartner(models.Model):

    _inherit = 'res.partner'

    # TODO: vai company_registry?
    business_code = fields.Char(
        'Business ID',
        help='The unique business registry identifier',
    )

    edicode = fields.Char(
        string="Edicode"
    )

    einvoice_operator_id = fields.Many2one(
        comodel_name="res.partner.operator.einvoice",
        string="eInvoice Operator",
        help="Intermediator for eInvoice documents",
    )
