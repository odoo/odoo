from odoo import models, fields

class OnedeskUnit(models.Model):
    _name = 'onedesk.unit'
    _description = 'Unité de propriété'

    name = fields.Char(string="Nom de l'unité", required=True)
    property_id = fields.Many2one('onedesk.property', string="Propriété")
    price = fields.Float(string="Prix")

    # ✅ Champ manquant
    available = fields.Boolean(string="Disponible", default=True)
