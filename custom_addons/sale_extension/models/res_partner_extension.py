from odoo import fields, models, api

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

    company_type = fields.Selection(default='person')

    floor = fields.Char(string="Piso", store=True)
    apartment = fields.Char(string="Departamento", store=True)
    cuit = fields.Char(string="CUIT", store=True)

    delivery_street = fields.Char(string="Street", store=True)
    delivery_floor = fields.Char(string="Piso", store=True)
    delivery_apartment = fields.Char(string="Depeartamento", store=True)
    delivery_city = fields.Char(string="City", store=True)
    delivery_state_id = fields.Many2one('res.country.state', string="State", store=True)
    delivery_zip = fields.Char(string="ZIP", store=True)
    delivery_country_id = fields.Many2one('res.country', string="Country", store=True)
    delivery_cuit = fields.Char(string="CUIT", store=True)


    @api.model
    def action_import_csv(self):
        return {
        }
