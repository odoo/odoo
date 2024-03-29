from odoo import models, fields, api
from odoo.exceptions import ValidationError
class Reservation(models.Model):
    _name = 'reservation'
    _log_access = False
    nom = fields.Char(string="Description", required=True)
    salle_id = fields.Many2one('salle', string="Salle", required=True)
    date_debut = fields.Datetime(string="Date de début", required=True)
    date_fin = fields.Datetime(string="Date de fin", required=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('done', 'Terminée'),
        ('cancelled', 'Annulée')
    ], string="Statut", default='draft')

    @api.constrains('date_debut', 'date_fin')
    def _check_reservation_dates(self):
        for record in self:
            if record.date_debut > record.date_fin:
                raise ValidationError("La date de début doit être antérieure à la date de fin de la réservation.")

    @api.model
    def create(self, values):
        salle = self.env['salle'].browse(values['salle_id'])
        if salle.etat == 'occupee':
            raise ValidationError("La salle est déjà réservée pour les dates choisies.")
        return super(Reservation, self).create(values)