# mi_website_ext/models/res_company.py
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    portal_background_image = fields.Image(string="Imagen de Fondo del Portal")