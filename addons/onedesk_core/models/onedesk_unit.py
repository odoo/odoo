from odoo import models, fields, api

class OnedeskUnit(models.Model):
    _name = 'onedesk.unit'
    _description = 'Unité de propriété'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'property_id, name'

    # Informations de base
    name = fields.Char(string="Nom de l'unité", required=True, tracking=True)
    active = fields.Boolean(string='Actif', default=True)
    property_id = fields.Many2one('onedesk.property', string="Propriété", required=True, ondelete='cascade', tracking=True)

    unit_type = fields.Selection([
        ('standard', 'Standard'),
        ('deluxe', 'Deluxe'),
        ('suite', 'Suite'),
        ('penthouse', 'Penthouse'),
        ('studio', 'Studio'),
    ], string='Type d\'unité', default='standard')

    description = fields.Html(string='Description', translate=True)

    # Caractéristiques (héritées ou spécifiques)
    bedrooms = fields.Integer(string='Chambres', default=1)
    bathrooms = fields.Integer(string='Salles de bain', default=1)
    max_guests = fields.Integer(string='Capacité max', default=2, required=True)
    square_feet = fields.Float(string='Surface (m²)')
    floor_number = fields.Integer(string='Étage')

    # Équipements spécifiques à l'unité
    amenity_ids = fields.Many2many('onedesk.amenity', 'unit_amenity_rel', string='Équipements')

    # Images
    image_1920 = fields.Image(string='Image principale', max_width=1920, max_height=1920)
    image_128 = fields.Image(string='Image (128)', related='image_1920', max_width=128, max_height=128, store=True)
    image_ids = fields.Many2many('ir.attachment', 'unit_image_rel', 'unit_id', 'attachment_id',
                                  string='Galerie photos')

    # Tarification
    price = fields.Float(string="Prix / nuit", tracking=True)
    currency_id = fields.Many2one('res.currency', string='Devise',
                                   default=lambda self: self.env.company.currency_id)
    cleaning_fee = fields.Monetary(string='Frais de ménage', currency_field='currency_id')

    # Statut et disponibilité
    available = fields.Boolean(string="Disponible", default=True, tracking=True)

    status = fields.Selection([
        ('available', 'Disponible'),
        ('occupied', 'Occupé'),
        ('cleaning', 'En nettoyage'),
        ('maintenance', 'En maintenance'),
        ('blocked', 'Bloqué'),
    ], string='Statut', default='available', tracking=True)

    maintenance_status = fields.Selection([
        ('good', 'Bon état'),
        ('needs_attention', 'Nécessite attention'),
        ('under_repair', 'En réparation'),
    ], string='État de maintenance', default='good')

    # Nettoyage
    cleaning_status = fields.Selection([
        ('clean', 'Propre'),
        ('dirty', 'À nettoyer'),
        ('in_progress', 'En cours'),
    ], string='Statut nettoyage', default='clean', tracking=True)

    last_cleaned_date = fields.Datetime(string='Dernier nettoyage')

    # Relations
    reservation_ids = fields.One2many('onedesk.reservation', 'unit_id', string='Réservations')
    reservation_count = fields.Integer(string='Nb réservations', compute='_compute_reservation_count')

    # Notes
    notes = fields.Text(string='Notes internes')

    @api.depends('reservation_ids')
    def _compute_reservation_count(self):
        for record in self:
            record.reservation_count = len(record.reservation_ids)
