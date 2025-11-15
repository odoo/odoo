from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class OneDeskReservation(models.Model):
    _name = 'onedesk.reservation'
    _description = 'Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    # Référence et statut
    name = fields.Char(string='Référence réservation', required=True, copy=False, default='New', tracking=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('checked_in', 'Check-in effectué'),
        ('checked_out', 'Check-out effectué'),
        ('cancelled', 'Annulée'),
        ('no_show', 'No-show'),
    ], string='Statut', default='draft', required=True, tracking=True)

    # Informations principales
    unit_id = fields.Many2one('onedesk.unit', string='Unité', required=True, tracking=True)
    property_id = fields.Many2one('onedesk.property', string='Propriété', related='unit_id.property_id', store=True, readonly=True)

    start_date = fields.Datetime(string='Date début', required=True, tracking=True)
    end_date = fields.Datetime(string='Date fin', required=True, tracking=True)
    nights = fields.Integer(string='Nuits', compute='_compute_nights', store=True)

    # Client
    partner_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True)
    guest_name = fields.Char(string='Nom du client')
    guest_email = fields.Char(string='Email')
    guest_phone = fields.Char(string='Téléphone')

    # Informations sur les invités
    guest_count = fields.Integer(string='Nombre total invités', default=1)
    adults = fields.Integer(string='Adultes', default=1)
    children = fields.Integer(string='Enfants', default=0)
    infants = fields.Integer(string='Bébés', default=0)
    pets = fields.Integer(string='Animaux', default=0)

    # Informations financières
    currency_id = fields.Many2one('res.currency', string='Devise',
                                   default=lambda self: self.env.company.currency_id,
                                   required=True)

    base_price = fields.Monetary(string='Prix de base', currency_field='currency_id')
    cleaning_fee = fields.Monetary(string='Frais de ménage', currency_field='currency_id')
    service_fee = fields.Monetary(string='Frais de service', currency_field='currency_id')
    extra_fee = fields.Monetary(string='Frais supplémentaires', currency_field='currency_id')
    tax_amount = fields.Monetary(string='Taxes', currency_field='currency_id')
    total_price = fields.Monetary(string='Prix total', currency_field='currency_id', compute='_compute_total_price', store=True)

    commission_rate = fields.Float(string='Taux de commission (%)', default=0.0)
    commission_amount = fields.Monetary(string='Montant commission', currency_field='currency_id', compute='_compute_commission', store=True)

    # Paiement
    payment_status = fields.Selection([
        ('pending', 'En attente'),
        ('partial', 'Partiel'),
        ('paid', 'Payé'),
        ('refunded', 'Remboursé'),
    ], string='Statut paiement', default='pending', tracking=True)

    payment_method = fields.Selection([
        ('card', 'Carte bancaire'),
        ('cash', 'Espèces'),
        ('bank_transfer', 'Virement bancaire'),
        ('platform', 'Plateforme (Airbnb/Booking)'),
        ('other', 'Autre'),
    ], string='Méthode de paiement')

    security_deposit = fields.Monetary(string='Caution', currency_field='currency_id')

    # Plateforme et intégration
    source_platform = fields.Selection([
        ('direct', 'Réservation directe'),
        ('airbnb', 'Airbnb'),
        ('booking', 'Booking.com'),
        ('vrbo', 'VRBO/Abritel'),
        ('other', 'Autre'),
    ], string='Plateforme source', default='direct', tracking=True)

    booking_channel = fields.Char(string='Canal de réservation')
    confirmation_code = fields.Char(string='Code de confirmation', tracking=True)

    external_id = fields.Char(string='ID Externe', index=True,
                              help="ID de la plateforme externe (Airbnb, Booking, etc.)")
    integration_id = fields.Many2one('onedesk.integration', string='Source intégration',
                                     help="Intégration depuis laquelle cette réservation a été importée")

    # Communication
    check_in_instructions = fields.Html(string='Instructions check-in')
    special_requests = fields.Text(string='Demandes spéciales')
    guest_notes = fields.Text(string='Notes client')
    internal_notes = fields.Text(string='Notes internes')

    # Check-in / Check-out
    actual_checkin_date = fields.Datetime(string='Check-in réel')
    actual_checkout_date = fields.Datetime(string='Check-out réel')

    # Évaluations
    guest_rating = fields.Selection([
        ('1', '★'),
        ('2', '★★'),
        ('3', '★★★'),
        ('4', '★★★★'),
        ('5', '★★★★★'),
    ], string='Note client')

    host_rating = fields.Selection([
        ('1', '★'),
        ('2', '★★'),
        ('3', '★★★'),
        ('4', '★★★★'),
        ('5', '★★★★★'),
    ], string='Note hôte')

    review_text = fields.Text(string='Commentaire')

    # Relations
    task_ids = fields.One2many('onedesk.task', 'reservation_id', string='Tâches')
    task_count = fields.Integer(string='Nombre de tâches', compute='_compute_task_count')

    # Lien vers l'événement du calendrier
    calendar_event_id = fields.Many2one('calendar.event', string='Événement calendrier', readonly=True)

    # Computed fields
    @api.depends('start_date', 'end_date')
    def _compute_nights(self):
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.nights = delta.days
            else:
                record.nights = 0

    @api.depends('base_price', 'cleaning_fee', 'service_fee', 'extra_fee', 'tax_amount')
    def _compute_total_price(self):
        for record in self:
            record.total_price = (record.base_price + record.cleaning_fee +
                                 record.service_fee + record.extra_fee + record.tax_amount)

    @api.depends('total_price', 'commission_rate')
    def _compute_commission(self):
        for record in self:
            if record.commission_rate > 0:
                record.commission_amount = record.total_price * (record.commission_rate / 100)
            else:
                record.commission_amount = 0.0

    @api.depends('task_ids')
    def _compute_task_count(self):
        for record in self:
            record.task_count = len(record.task_ids)

    # Méthodes de workflow
    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_check_in(self):
        self.write({
            'state': 'checked_in',
            'actual_checkin_date': fields.Datetime.now()
        })

    def action_check_out(self):
        self.write({
            'state': 'checked_out',
            'actual_checkout_date': fields.Datetime.now()
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_set_no_show(self):
        self.write({'state': 'no_show'})

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

    # Validation des conflits de réservation
    @api.constrains('unit_id', 'start_date', 'end_date')
    def _check_reservation_overlap(self):
        """Vérifie qu'il n'y a pas de chevauchement de réservations pour la même unité"""
        for reservation in self:
            # Vérifier que start_date < end_date
            if reservation.start_date >= reservation.end_date:
                raise ValidationError(
                    f"La date de début ({reservation.start_date}) doit être antérieure "
                    f"à la date de fin ({reservation.end_date})."
                )

            # Chercher les réservations qui se chevauchent pour la même unité
            overlapping = self.search([
                ('unit_id', '=', reservation.unit_id.id),
                ('id', '!=', reservation.id),  # Exclure la réservation actuelle
                ('start_date', '<', reservation.end_date),
                ('end_date', '>', reservation.start_date),
            ])

            if overlapping:
                overlap_details = "\n".join([
                    f"  - {r.name}: {r.start_date} à {r.end_date}"
                    for r in overlapping
                ])
                raise ValidationError(
                    f"⚠️ Conflit de réservation détecté!\n\n"
                    f"L'unité '{reservation.unit_id.name}' est déjà réservée pendant cette période:\n"
                    f"{overlap_details}\n\n"
                    f"Votre réservation: {reservation.start_date} à {reservation.end_date}"
                )