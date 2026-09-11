from odoo import fields, models, api


class ModelName(models.Model):
    _inherit = 'res.company'

    google_api_key = fields.Char(string="API Key")
