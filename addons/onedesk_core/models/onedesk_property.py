from odoo import models, fields

class OnedeskProperty(models.Model):
    _name = 'onedesk.property'
    _description = 'Propriété OneDesk'

    name = fields.Char(string="Nom de la propriété", required=True)
    address = fields.Char(string="Adresse")
    price = fields.Float(string="Prix")

    # ✅ Ces deux champs sont indispensables pour la vue calendrier
    date_start = fields.Date(string="Date de début")
    date_stop = fields.Date(string="Date de fin")

    user_id = fields.Many2one('res.users', string="Responsable", default=lambda self: self.env.user)
