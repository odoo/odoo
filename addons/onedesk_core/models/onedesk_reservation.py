from odoo import models, fields, api

class OneDeskReservation(models.Model):
    _name = 'onedesk.reservation'
    _description = 'Reservation'

    # Champs de base
    name = fields.Char(string='Reservation Reference', required=True, copy=False, default='New')
    unit_id = fields.Many2one('onedesk.unit', string='Unit', required=True)
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)

    # Champs intégration
    external_id = fields.Char(string='ID Externe', index=True, 
                              help="ID de la plateforme externe (Airbnb, Booking, etc.)")
    integration_id = fields.Many2one('onedesk.integration', string='Source plateforme',
                                     help="Intégration depuis laquelle cette réservation a été importée")

    # Lien vers l'événement du calendrier
    calendar_event_id = fields.Many2one('calendar.event', string='Calendar Event', readonly=True)

    # Création automatique de l'événement
    @api.model
    def create(self, vals):
        reservation = super().create(vals)

        # Crée un événement dans le calendrier visible pour tout le monde
        event = self.env['calendar.event'].sudo().create({
            'name': f"{reservation.name} - {reservation.unit_id.name}",
            'start': reservation.start_date,
            'stop': reservation.end_date,
            'description': f"Client: {reservation.partner_id.name}\nUnité: {reservation.unit_id.name}",
            'location': reservation.unit_id.name,
            'allday': False,
            'privacy': 'public',
            'show_as': 'busy',
        })

        # Lier l'événement à la réservation
        reservation.calendar_event_id = event.id
        return reservation

    # Mise à jour automatique de l'événement si la réservation change
    def write(self, vals):
        res = super().write(vals)
        for reservation in self:
            if reservation.calendar_event_id:
                reservation.calendar_event_id.sudo().write({
                    'name': f"{reservation.name} - {reservation.unit_id.name}",
                    'start': reservation.start_date,
                    'stop': reservation.end_date,
                    'description': f"Client: {reservation.partner_id.name}\nUnité: {reservation.unit_id.name}",
                    'location': reservation.unit_id.name,
                })
        return res

    # Suppression automatique de l'événement si la réservation est supprimée
    def unlink(self):
        for reservation in self:
            if reservation.calendar_event_id:
                reservation.calendar_event_id.sudo().unlink()
        return super().unlink()