from odoo import models, fields

class SaaSClient(models.Model):
    _name = 'saas.client'
    _description = 'Client SaaS'

    name = fields.Char(string="Nom du Client", required=True)
    email = fields.Char(string="Email", required=True)
    db_name = fields.Char(string="Nom de la Base", required=True)
    pack_id = fields.Many2one('saas.pack', string="Pack")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'Actif'),
        ('suspended', 'Suspendu')
    ], default='draft')