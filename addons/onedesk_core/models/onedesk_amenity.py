from odoo import models, fields

class OnedeskAmenity(models.Model):
    _name = 'onedesk.amenity'
    _description = 'Équipement/Commodité'
    _order = 'category, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    category = fields.Selection([
        ('essential', 'Essentiel'),
        ('comfort', 'Confort'),
        ('entertainment', 'Divertissement'),
        ('safety', 'Sécurité'),
        ('outdoor', 'Extérieur'),
        ('other', 'Autre'),
    ], string='Catégorie', default='other', required=True)

    icon = fields.Char(string='Icône', help='Code icône FontAwesome (ex: fa-wifi)')
    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean(string='Actif', default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Ce nom d\'équipement existe déjà!')
    ]
