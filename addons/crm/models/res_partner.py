import logging
import requests
import time
from markupsafe import escape

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    centralita_number = fields.Char(string="Número de Centralita")
    trade_name = fields.Char(
        string="Marca Comercial",
        help="Nombre comercial de la empresa",
    )
    fax = fields.Char(string="Fax")

    first_name = fields.Char(string="Nombre de pila")
    last_name = fields.Char(string="Apellidos")
    account_name = fields.Char(
        string="Nombre de cuenta",
        related="parent_id.name",
        store=True,
        readonly=True,
    )
    preferred_contact_method = fields.Selection(
        selection=[
            ("any", "Cualquiera"),
            ("email", "Correo electrónico"),
            ("phone", "Teléfono del trabajo"),
            ("mobile", "Teléfono móvil"),
        ],
        string="Forma de contacto preferida",
        default="any",
    )

    main_contact_id = fields.Many2one(
        'res.partner',
        string="Contacto principal",
        domain="[('parent_id', '=', id), ('type', '=', 'contact')]",
    )
    service_address = fields.Text(string="Dirección de servicio")

    def _selection_relationship_type(self):
        types = self.env['crm.relationship.type'].search(
            [('active', '=', True)],
            order='sequence, name',
        )
        return [(rel_type.code, rel_type.name) for rel_type in types]

    relationship_type = fields.Selection(
        selection=_selection_relationship_type,
        string="Tipo de relación",
    )
    lopd_signed = fields.Boolean(string="LOPD firmada", default=False)
    lopd_document_id = fields.Many2one(
        'ir.attachment',
        string="Documento LOPD",
        help="Archivo PDF o documento de la LOPD firmada",
    )
    billing_prepago = fields.Boolean(string="Cliente prepago", default=False)
    billing_payment_method = fields.Selection(
        selection=[
            ('contado', 'Contado'),
            ('transferencia', 'Transferencia'),
            ('sepa', 'SEPA'),
        ],
        string="Forma de pago",
        default='contado',
    )
    billing_invoice_email = fields.Char(string="Email facturación")
    billing_sepa_signed = fields.Boolean(string="SEPA firmado", default=False)
    billing_irpf_retention = fields.Float(string="Retenciones IRPF (%)", digits=(5, 2))
    billing_incidents_cobro = fields.Selection(
        selection=[
            ('no', 'No'),
            ('si', 'Sí'),
        ],
        string="Incidencias cobro",
        default='no',
    )
    billing_default_product = fields.Char(string="Producto")
    billing_default_pricelist = fields.Char(string="Lista de precios por defecto")
    billing_sepa_document_id = fields.Many2one(
        'ir.attachment',
        string="Documento SEPA",
        help="Documento de mandato SEPA firmado",
    )
    notes = fields.Text(string="Notas")

    contact_count = fields.Integer(
        string="Número de Contactos",
        compute='_compute_contact_count',
    )

    outlook_message_count = fields.Integer(
        string='Mensajes Outlook',
        compute='_compute_outlook_message_count',
    )

    contract_it_bonus = fields.Boolean(string="Bono informática", default=False)
    contract_total_it_maintenance = fields.Boolean(
        string="Mantenimiento total informática",
        default=False,
    )
    contract_physical_centralita = fields.Boolean(
        string="Mantenimiento centralita física",
        default=False,
    )
    contract_cloud_centralita = fields.Boolean(
        string="Mantenimiento centralita cloud",
        default=False,
    )
    contract_vpn = fields.Boolean(string="Mantenimiento VPN", default=False)
    contract_acronis = fields.Boolean(string="Acronis", default=False)
    contract_antivirus = fields.Boolean(string="Antivirus", default=False)
    contract_office365 = fields.Boolean(string="Office 365", default=False)
    contract_incidents_cobro = fields.Boolean(string="Incidencias cobro", default=False)

    street_number = fields.Char(
        string="Número",
        help="Número de la calle",
    )

    latitude = fields.Float(
        string="Latitud",
        digits=(10, 8),
        help="Latitud de la ubicación",
    )
    longitude = fields.Float(
        string="Longitud",
        digits=(10, 8),
        help="Longitud de la ubicación",
    )
    geocode_address = fields.Char(
        string="Dirección geocodificada",
        readonly=True,
        help="Última dirección usada para geocodificar",
    )
    last_geocode = fields.Datetime(
        string="Última geocodificación",
        readonly=True,
        help="Fecha y hora de la última geocodificación",
    )
    map_html = fields.Html(
        string="Mapa",
        compute='_compute_map_html',
        sanitize=False,
        help="Mapa con la ubicación de la dirección",
    )
    contact_map_html = fields.Html(
        string="Mapa del contacto",
        compute='_compute_contact_map_html',
        sanitize=False,
        help="Mapa del contacto (usa la ubicación de la cuenta cuando el contacto no tenga dirección propia)",
    )
    location_detected_html = fields.Html(
        string="Ubicación detectada",
        compute='_compute_location_detected_html',
        sanitize=False,
        help="Representación formateada de la ubicación detectada",
    )
    location_search = fields.Char(
        string="Buscar",
        help="Filtra ubicaciones añadidas manualmente por nombre o dirección",
    )
    location_show_active_only = fields.Boolean(
        string="Mostrar activos",
        default=True,
        help="Muestra solo ubicaciones activas",
    )
    location_ids = fields.One2many(
        'crm.partner.location',
        'partner_id',
        string="Ubicaciones",
        help="Ubicaciones/sedes añadidas manualmente para esta cuenta",
    )
    associated_company_ids = fields.One2many(
        'res.partner',
        'parent_id',
        string="Sedes asociadas",
        domain=[('is_company', '=', True)],
        help="Cuentas hijas asociadas a esta empresa (sedes)",
    )

    @api.depends('first_name', 'last_name', 'is_company')
    def _compute_contact_display_name(self):
        for partner in self:
            if partner.is_company:
                continue
            first = (partner.first_name or '').strip()
            last = (partner.last_name or '').strip()
            full_name = ' '.join(p for p in [first, last] if p)
            if full_name and partner.name != full_name:
                partner.name = full_name

    @api.onchange('first_name', 'last_name')
    def _onchange_first_last_name(self):
        for partner in self:
            if partner.is_company:
                continue
            first = (partner.first_name or '').strip()
            last = (partner.last_name or '').strip()
            partner.name = ' '.join(p for p in [first, last] if p)

    @api.depends('latitude', 'longitude')
    def _compute_map_html(self):
        for partner in self:
            if partner.latitude and partner.longitude:
                partner.map_html = partner._build_centered_osm_map_html(partner.latitude, partner.longitude, 400)
            else:
                partner.map_html = (
                    '<div style="padding: 20px; text-align: center; color: #999; background: #f9f9f9; '
                    'border-radius: 4px; border: 1px dashed #ddd;"><p>Selecciona una dirección para ver el mapa</p></div>'
                )

    @api.depends('latitude', 'longitude', 'parent_id.latitude', 'parent_id.longitude')
    def _compute_contact_map_html(self):
        for partner in self:
            lat = partner.latitude
            lon = partner.longitude

            if (not lat or not lon) and partner.parent_id:
                lat = partner.parent_id.latitude
                lon = partner.parent_id.longitude

            if lat and lon:
                partner.contact_map_html = partner._build_centered_osm_map_html(lat, lon, 320)
            else:
                partner.contact_map_html = (
                    '<div style="padding: 20px; text-align: center; color: #999; background: #f9f9f9; '
                    'border-radius: 4px; border: 1px dashed #ddd;">'
                    '<p>Selecciona o escribe una dirección para ver la ubicación</p>'
                    '</div>'
                )

    def _build_centered_osm_map_html(self, lat, lon, height):
        bbox_margin = 0.003
        bbox = f"{lon - bbox_margin},{lat - bbox_margin},{lon + bbox_margin},{lat + bbox_margin}"
        return (
            f'<div style="width: 100%; height: {height}px; border-radius: 4px; overflow: hidden; '
            'box-shadow: 0 1px 3px rgba(0,0,0,0.12);">'
            f'<iframe width="100%" height="100%" frameborder="0" scrolling="no" marginheight="0" '
            f'marginwidth="0" src="https://www.openstreetmap.org/export/embed.html?bbox={bbox}&amp;'
            f'layer=mapnik&amp;marker={lat},{lon}" style="border: 0; width: 100%; height: 100%;"></iframe>'
            '</div>'
        )

    @api.onchange('parent_id')
    def _onchange_parent_id_copy_address(self):
        for partner in self:
            if partner.is_company or not partner.parent_id:
                continue

            has_own_address = any([
                partner.street,
                partner.street_number,
                partner.street2,
                partner.zip,
                partner.city,
                partner.state_id,
                partner.country_id,
                partner.latitude,
                partner.longitude,
            ])

            if has_own_address:
                continue

            partner.street = partner.parent_id.street
            partner.street_number = partner.parent_id.street_number
            partner.street2 = partner.parent_id.street2
            partner.zip = partner.parent_id.zip
            partner.city = partner.parent_id.city
            partner.state_id = partner.parent_id.state_id
            partner.country_id = partner.parent_id.country_id
            partner.latitude = partner.parent_id.latitude
            partner.longitude = partner.parent_id.longitude

    @api.depends(
        'location_search',
        'location_show_active_only',
        'location_ids',
        'location_ids.name',
        'location_ids.street',
        'location_ids.street_number',
        'location_ids.street2',
        'location_ids.zip',
        'location_ids.city',
        'location_ids.state_id',
        'location_ids.country_id',
        'location_ids.active',
    )
    def _compute_location_detected_html(self):
        for partner in self:
            search_value = (partner.location_search or '').strip().lower()
            locations = partner.location_ids
            if partner.location_show_active_only:
                locations = locations.filtered(lambda location: location.active)

            if search_value:
                locations = locations.filtered(
                    lambda location: search_value in (
                        f"{location.name or ''} {location._build_full_address() or ''}".lower()
                    )
                )

            if locations:
                rows = []
                for location in locations.sorted(key=lambda record: (record.sequence, (record.name or '').lower())):
                    rows.append(
                        '<tr>'
                        f'<td style="padding:8px 12px;border-bottom:1px solid #ececec;color:#333;">{escape(location.name or "Nueva ubicación")}</td>'
                        f'<td style="padding:8px 12px;border-bottom:1px solid #ececec;color:#333;">{escape(location._build_full_address() or "Sin ubicación detectada")}</td>'
                        '</tr>'
                    )
                partner.location_detected_html = (
                    '<div style="border:1px solid #d6d6d6;border-radius:4px;background:#fff;overflow:hidden;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<thead>'
                    '<tr style="background:#f7f7f7;">'
                    '<th style="text-align:left;padding:8px 12px;border-bottom:1px solid #e6e6e6;color:#555;">Ubicación</th>'
                    '<th style="text-align:left;padding:8px 12px;border-bottom:1px solid #e6e6e6;color:#555;">Dirección</th>'
                    '</tr>'
                    '</thead>'
                    f'<tbody>{"".join(rows)}</tbody>'
                    '</table>'
                    '</div>'
                )
            else:
                partner.location_detected_html = (
                    '<div style="padding:20px; text-align:center; color:#999; background:#f9f9f9; '
                    'border-radius:4px; border:1px dashed #ddd;">'
                    '<p>No hay ubicaciones añadidas</p>'
                    '</div>'
                )

    def _build_full_address(self):
        self.ensure_one()
        parts = []

        if self.street:
            street_part = self.street
            if self.street_number:
                street_part = f"{self.street}, {self.street_number}"
            parts.append(street_part)

        if self.street2:
            parts.append(self.street2)
        if self.zip:
            parts.append(self.zip)
        if self.city:
            parts.append(self.city)
        if self.state_id:
            parts.append(self.state_id.name)
        if self.country_id:
            parts.append(self.country_id.name)

        return ', '.join(parts)

    def action_geocode_address(self):
        for partner in self:
            address = partner._build_full_address()
            if not address or (partner.geocode_address == address and partner.latitude):
                continue

            time.sleep(1)

            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1,
            }
            headers = {'User-Agent': 'Odoo/CRM Geocode'}

            try:
                resp = requests.get(
                    'https://nominatim.openstreetmap.org/search',
                    params=params,
                    headers=headers,
                    timeout=10,
                )
                data = resp.json() if resp.ok else []
                if data:
                    lat = float(data[0]['lat'])
                    lon = float(data[0]['lon'])
                    partner.write({
                        'latitude': lat,
                        'longitude': lon,
                        'last_geocode': fields.Datetime.now(),
                        'geocode_address': address,
                    })
                    _logger.info('Geocodificación exitosa para %s: %s, %s', partner.name, lat, lon)
            except Exception as e:
                _logger.warning('Error geocodificando dirección para %s: %s', partner.name, e)

    @api.model
    def action_reverse_geocode(self, lat, lon):
        params = {
            'lat': lat,
            'lon': lon,
            'format': 'json',
            'addressdetails': 1,
        }
        headers = {'User-Agent': 'Odoo/CRM Reverse Geocode'}

        try:
            resp = requests.get(
                'https://nominatim.openstreetmap.org/reverse',
                params=params,
                headers=headers,
                timeout=10,
            )
            data = resp.json() if resp.ok else {}
            addr = data.get('address', {})

            country = self.env['res.country'].search(
                [('code', '=', (addr.get('country_code') or '').upper())],
                limit=1,
            )
            state = (
                self.env['res.country.state'].search(
                    [('name', 'ilike', addr.get('state', '')), ('country_id', '=', country.id)],
                    limit=1,
                )
                if country
                else None
            )

            city_name = addr.get('city') or addr.get('town') or addr.get('village')

            city = False
            if city_name and state:
                city = self.env['res.city'].search(
                    [('name', 'ilike', city_name), ('state_id', '=', state.id)],
                    limit=1,
                )

            result = {
                'street': addr.get('road') or '',
                'street_number': addr.get('house_number') or '',
                'street2': '',
                'zip': addr.get('postcode') or '',
                'city': city_name or '',
                'state_id': state.id if state else False,
                'country_id': country.id if country else False,
            }
            if city:
                result['city_id'] = city.id

            return result
        except Exception as e:
            _logger.warning('Error en reverse geocode: %s', e)
            return {}

    def action_view_on_map(self):
        self.ensure_one()
        if not self.latitude or not self.longitude:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin coordenadas'),
                    'message': _('Este contacto no tiene coordenadas GPS. Use el botón "Actualizar Coordenadas" para geocodificar la dirección.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        zoom = 15
        url = f'https://www.openstreetmap.org/?mlat={self.latitude}&mlon={self.longitude}&zoom={zoom}'
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_open_website(self):
        self.ensure_one()
        website = (self.website or '').strip()
        if not website:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin sitio web'),
                    'message': _('Esta cuenta no tiene sitio web configurado.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        if not website.startswith(('http://', 'https://')):
            website = f'https://{website}'
        return {
            'type': 'ir.actions.act_url',
            'url': website,
            'target': 'new',
        }

    def _compute_outlook_message_count(self):
        for partner in self:
            partner.outlook_message_count = self.env['mail.message'].search_count([
                ('res_id', '=', partner.id),
                ('model', '=', 'res.partner'),
                ('message_type', '=', 'email'),
            ])

    def action_send_outlook_message(self):
        self.ensure_one()
        if not self.email:
            raise ValidationError(_('Este contacto no tiene dirección de correo electrónico.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Enviar mensaje por Outlook'),
            'res_model': 'outlook.message.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_email_to': self.email,
                'default_partner_name': self.name,
            },
        }

    def action_view_outlook_messages(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mensajes de Outlook'),
            'res_model': 'mail.message',
            'view_mode': 'list,form',
            'domain': [
                ('res_id', '=', self.id),
                ('model', '=', 'res.partner'),
                ('message_type', '=', 'email'),
            ],
            'context': {'create': False},
        }

    @api.depends('child_ids', 'child_ids.type')
    def _compute_contact_count(self):
        for partner in self:
            if partner.is_company:
                partner.contact_count = len(partner.child_ids.filtered(lambda c: c.type == 'contact'))
            else:
                partner.contact_count = 0

    def action_view_contacts(self):
        self.ensure_one()
        return {
            'name': f'Contactos de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id), ('type', '=', 'contact')],
            'context': {
                'default_parent_id': self.id,
                'default_type': 'contact',
                'default_is_company': False,
            },
        }

    @api.constrains('lopd_signed', 'lopd_document_id')
    def _check_lopd_document(self):
        for partner in self:
            if partner.lopd_signed and not partner.lopd_document_id:
                raise ValidationError(
                    _("Si marca la LOPD como firmada, debe importar el documento mediante el botón 'Importar documento LOPD'.")
                )

    @api.constrains('billing_sepa_signed', 'billing_sepa_document_id')
    def _check_billing_sepa_document(self):
        for partner in self:
            if partner.billing_sepa_signed and not partner.billing_sepa_document_id:
                raise ValidationError(
                    _("Si marca SEPA como firmado, debe adjuntar el documento mediante el botón 'Adjuntar documento SEPA'.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['type'] = 'contact'
            is_company = vals.get('is_company', False)
            if not is_company:
                first = (vals.get('first_name') or '').strip()
                last = (vals.get('last_name') or '').strip()
                if first or last:
                    vals['name'] = ' '.join(p for p in [first, last] if p)
        return super().create(vals_list)

    def write(self, vals):
        if 'is_company' in vals:
            vals['type'] = 'contact'

        if 'name' not in vals and ('first_name' in vals or 'last_name' in vals):
            for partner in self:
                partner_vals = dict(vals)
                if not partner.is_company:
                    first = (partner_vals.get('first_name', partner.first_name) or '').strip()
                    last = (partner_vals.get('last_name', partner.last_name) or '').strip()
                    partner_vals['name'] = ' '.join(p for p in [first, last] if p)
                super(Partner, partner).write(partner_vals)
            return True

        return super().write(vals)

    @api.onchange('is_company')
    def _onchange_is_company(self):
        self.type = 'contact'

    def action_import_lopd_document(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Importar Documento LOPD',
            'res_model': 'lopd.document.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('crm.view_lopd_document_wizard_form').id,
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_document_type': 'lopd',
                'default_name': f'LOPD_{self.name}',
            },
        }

    def action_import_sepa_document(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Importar Documento SEPA',
            'res_model': 'lopd.document.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('crm.view_lopd_document_wizard_form').id,
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_document_type': 'sepa',
                'default_name': f'SEPA_{self.name}',
            },
        }


class PartnerLocation(models.Model):
    _name = 'crm.partner.location'
    _description = 'Ubicación manual de cuenta'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one('res.partner', string='Cuenta', required=True, ondelete='cascade')
    name = fields.Char(string='Ubicación', required=True)
    street = fields.Char(string='Calle')
    street_number = fields.Char(string='Nº')
    street2 = fields.Char(string='Portal / Piso / Oficina')
    city = fields.Char(string='Ciudad')
    zip = fields.Char(string='Código postal')
    state_id = fields.Many2one('res.country.state', string='Provincia')
    country_id = fields.Many2one('res.country', string='País')
    active = fields.Boolean(default=True)

    def _build_full_address(self):
        self.ensure_one()
        parts = []

        if self.street:
            street_part = self.street
            if self.street_number:
                street_part = f"{self.street}, {self.street_number}"
            parts.append(street_part)

        if self.street2:
            parts.append(self.street2)
        if self.zip:
            parts.append(self.zip)
        if self.city:
            parts.append(self.city)
        if self.state_id:
            parts.append(self.state_id.name)
        if self.country_id:
            parts.append(self.country_id.name)

        return ', '.join(parts)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)

        if self.env.context.get('lopd_import') and self.env.context.get('partner_id'):
            partner_id = self.env.context.get('partner_id')
            partner = self.env['res.partner'].browse(partner_id)
            if attachments and partner.exists():
                partner.write({'lopd_document_id': attachments[0].id})

        return attachments
