from odoo import fields, models


class L10nInPortCode(models.Model):
    _inherit = 'l10n_in.port.code'

    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street 2")
    city = fields.Char(string="City")
    zip = fields.Char(string="Zip Code")
    country_id = fields.Many2one(string="Country", related='state_id.country_id')
