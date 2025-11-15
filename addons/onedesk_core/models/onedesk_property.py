from odoo import models, fields, api

class OnedeskProperty(models.Model):
    _name = 'onedesk.property'
    _description = 'Propriété OneDesk'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # Informations de base
    name = fields.Char(string="Nom de la propriété", required=True, tracking=True)
    active = fields.Boolean(string='Actif', default=True, tracking=True)
    property_type = fields.Selection([
        ('apartment', 'Appartement'),
        ('house', 'Maison'),
        ('villa', 'Villa'),
        ('studio', 'Studio'),
        ('chalet', 'Chalet'),
        ('cottage', 'Cottage'),
        ('other', 'Autre'),
    ], string='Type de propriété', default='apartment', required=True, tracking=True)

    description = fields.Html(string='Description', translate=True)

    # Localisation
    address = fields.Char(string="Adresse complète", tracking=True)
    street = fields.Char(string='Rue')
    street2 = fields.Char(string='Complément')
    city = fields.Char(string='Ville', tracking=True)
    state_id = fields.Many2one('res.country.state', string='État/Province')
    zip = fields.Char(string='Code postal')
    country_id = fields.Many2one('res.country', string='Pays', default=lambda self: self.env.ref('base.fr', raise_if_not_found=False))

    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))

    # Caractéristiques
    bedrooms = fields.Integer(string='Nombre de chambres', default=1)
    bathrooms = fields.Integer(string='Nombre de salles de bain', default=1)
    max_guests = fields.Integer(string='Capacité max (personnes)', default=2, required=True)
    square_feet = fields.Float(string='Surface (m²)')
    floor_number = fields.Integer(string='Étage')

    # Équipements
    amenity_ids = fields.Many2many('onedesk.amenity', string='Équipements')

    # Images
    image_1920 = fields.Image(string='Image principale', max_width=1920, max_height=1920)
    image_128 = fields.Image(string='Image (128)', related='image_1920', max_width=128, max_height=128, store=True)
    image_ids = fields.Many2many('ir.attachment', 'property_image_rel', 'property_id', 'attachment_id',
                                  string='Galerie photos')

    # Règles de la maison
    check_in_time = fields.Float(string='Heure check-in', default=15.0, help='Heure au format 24h (ex: 15.0 pour 15h00)')
    check_out_time = fields.Float(string='Heure check-out', default=11.0, help='Heure au format 24h')
    minimum_stay = fields.Integer(string='Séjour minimum (nuits)', default=1)
    maximum_stay = fields.Integer(string='Séjour maximum (nuits)', default=0, help='0 = illimité')

    pets_allowed = fields.Boolean(string='Animaux acceptés', default=False)
    smoking_allowed = fields.Boolean(string='Fumeur autorisé', default=False)
    events_allowed = fields.Boolean(string='Événements autorisés', default=False)

    house_rules = fields.Text(string='Règlement intérieur', translate=True)

    # Tarification
    price = fields.Float(string="Prix de base / nuit", tracking=True)
    currency_id = fields.Many2one('res.currency', string='Devise',
                                   default=lambda self: self.env.company.currency_id)
    cleaning_fee = fields.Monetary(string='Frais de ménage', currency_field='currency_id')
    extra_guest_fee = fields.Monetary(string='Frais par personne supplémentaire', currency_field='currency_id')

    # Gestion
    user_id = fields.Many2one('res.users', string="Gestionnaire", default=lambda self: self.env.user, tracking=True)
    owner_id = fields.Many2one('res.partner', string='Propriétaire', tracking=True)

    status = fields.Selection([
        ('available', 'Disponible'),
        ('occupied', 'Occupé'),
        ('maintenance', 'En maintenance'),
        ('inactive', 'Inactif'),
    ], string='Statut', default='available', compute='_compute_status', store=True)

    # Relations
    unit_ids = fields.One2many('onedesk.unit', 'property_id', string='Unités')
    unit_count = fields.Integer(string='Nombre d\'unités', compute='_compute_unit_count')

    # ✅ Ces deux champs sont indispensables pour la vue calendrier
    date_start = fields.Date(string="Date de début")
    date_stop = fields.Date(string="Date de fin")

    # Notes
    notes = fields.Text(string='Notes internes')

    @api.depends('unit_ids')
    def _compute_unit_count(self):
        for record in self:
            record.unit_count = len(record.unit_ids)

    @api.depends('unit_ids.available')
    def _compute_status(self):
        for record in self:
            if not record.active:
                record.status = 'inactive'
            elif record.unit_ids:
                if all(not unit.available for unit in record.unit_ids):
                    record.status = 'maintenance'
                elif any(not unit.available for unit in record.unit_ids):
                    record.status = 'occupied'
                else:
                    record.status = 'available'
            else:
                record.status = 'available'
