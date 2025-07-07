from odoo import models, fields

class SaaSPack(models.Model):
    _name = 'saas.pack'
    _description = 'Pack SaaS'

    name = fields.Char(string="Nom du Pack", required=True)
    module_ids = fields.Many2many(
        'ir.module.module',
        string="Modules Inclus"
    )
    price = fields.Float(string="Prix Mensuel")