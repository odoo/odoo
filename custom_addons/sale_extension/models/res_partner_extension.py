from odoo import fields, models

class ResPartnerExtension(models.Model):
    _inherit = 'res.partner'

    floor = fields.Char(
        string="Piso",
        readOnly=False,
        store=True,
        default=""
    )
    apartment = fields.Char(
        string="Departamento",
        readOnly=False,
        store=True,
        default=""
    ) 
    cuit = fields.Char(
        string="CUIT",
        store=True,
    )

    company_type = fields.Selection(default='person')
