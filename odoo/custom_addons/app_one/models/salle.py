from odoo import models, fields

class Salle(models.Model):
    _name = 'salle'
    _log_access = False
    _description = 'Modèle pour gérer les informations de salle'
    nom = fields.Char(string="Nom", required=True)
    capacite = fields.Integer(string="Capacité")
    etat = fields.Selection([
        ('disponible', 'Disponible'),
        ('occupee', 'Occupée'),
    ], string="État", default='disponible')