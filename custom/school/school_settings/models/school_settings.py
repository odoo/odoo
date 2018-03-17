from odoo import  models, fields, api


class SchoolSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'school.settings'