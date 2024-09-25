# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[
        ('pk_edi_json', 'Pakistan FBR(Federal Board of Revenue)')
    ])
