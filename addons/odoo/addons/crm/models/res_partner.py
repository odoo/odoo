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
        string="Tipo de relación (selección)",
    )
    relationship_type_id = fields.Many2one(
        'crm.relationship.type',
        string="Tipo de relación (registro)",
        compute='_compute_relationship_type_id',
        inverse='_inverse_relationship_type_id',
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
        string="Forma de pago (legacy)",
        default='contado',
    )
    billing_payment_method_id = fields.Many2one(
        'crm.payment.method',
        string="Forma de pago",
        compute='_compute_billing_payment_method_id',
        inverse='_inverse_billing_payment_method_id',
    )
    billing_payment_method_custom = fields.Char(string="Nueva forma de pago")
    billing_invoice_email = fields.Char(string="Email facturación")
    billing_sepa_signed = fields.Boolean(string="SEPA firmado", default=False)
    billing_irpf_retention = fields.Float(string="Retenciones IRPF (%)", digits=(5, 2))
    billing_incidents_cobro = fields.Selection(
        selection=[
            ('no', 'No'),
            ('si', 'Sí'),
        ],
        string="Incidencias cobro (facturación)",
        default='no',
    )
    contract_incidents_cobro = fields.Boolean(string="Incidencias cobro (contrato)", default=False)
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
    contract_extra_option_ids = fields.Many2many(
        'crm.contract.option',
        'res_partner_crm_contract_option_rel',
        'partner_id',
        'option_id',
        string="Contratos extra (interno)",
    )
    contract_extra_line_ids = fields.One2many(
        'crm.contract.option.line',
        'partner_id',
        string="Contratos extra",
    )

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
    available_location_ids = fields.Many2many(
        'crm.partner.location',
        compute='_compute_available_location_ids',
        string="Ubicaciones disponibles",
        help="Ubicaciones disponibles de la empresa principal",
    )
    location_id = fields.Many2one(
        'crm.partner.location',
        string="Ubicación",
        domain="[('id', 'in', available_location_ids)]",
        help="Ubicación/sede seleccionada para esta cuenta o contacto",
    )
    associated_company_ids = fields.One2many(
        'res.partner',
        'parent_id',
        string="Sedes asociadas",
        domain=[('is_company', '=', True)],
        help="Cuentas hijas asociadas a esta empresa (sedes)",
    )

    def get_formview_id(self, access_uid=None):
        self.ensure_one()
        if self.is_company:
            return self.env.ref('crm.view_partner_form_crm_company').id
        return self.env.ref('crm.view_partner_form_crm_person').id

    def unlink(self):
        if 'calendar.filters' in self.env:
            self.env['calendar.filters'].search([('partner_id', 'in', self.ids)]).unlink()
        return super().unlink()

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

    @api.depends('relationship_type')
    def _compute_relationship_type_id(self):
        relation_types = self.env['crm.relationship.type'].search([])
        relation_type_map = {relation_type.code: relation_type for relation_type in relation_types}
        for partner in self:
            partner.relationship_type_id = relation_type_map.get(partner.relationship_type)

    def _inverse_relationship_type_id(self):
        for partner in self:
            partner.relationship_type = partner.relationship_type_id.code if partner.relationship_type_id else False

    @api.depends('billing_payment_method')
    def _compute_billing_payment_method_id(self):
        payment_methods = self.env['crm.payment.method'].search([])
        payment_method_map = {payment_method.code: payment_method for payment_method in payment_methods}
        for partner in self:
            partner.billing_payment_method_id = payment_method_map.get(partner.billing_payment_method)

    def _inverse_billing_payment_method_id(self):
        for partner in self:
            partner.billing_payment_method = partner.billing_payment_method_id.code if partner.billing_payment_method_id else False

    @api.depends(
        'is_company',
        'parent_id',
        'parent_id.is_company',
        'parent_id.parent_id',
        'location_ids',
        'parent_id.location_ids',
    )
    def _compute_available_location_ids(self):
        for partner in self:
            main_company = partner._get_main_company_for_locations()
            if main_company:
                partner.available_location_ids = main_company.location_ids
            else:
                partner.available_location_ids = partner.location_ids

    def _get_main_company_for_locations(self):
        self.ensure_one()

        company = self if self.is_company else self.parent_id
        if not company:
            return False

        while company.parent_id and company.parent_id.is_company:
            company = company.parent_id

        return company if company.is_company else False

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

    @api.onchange('parent_id', 'is_company')
    def _onchange_parent_locations_domain(self):
        main_company = self._get_main_company_for_locations()
        available = main_company.location_ids if main_company else self.location_ids

        if self.location_id and self.location_id not in available:
            self.location_id = False

        return {'domain': {'location_id': [('id', 'in', available.ids)]}}

    @api.onchange('location_id')
    def _onchange_location_id_fill_address(self):
        for partner in self:
            location = partner.location_id
            if not location:
                continue

            partner.street = location.street or location.name
            partner.street_number = location.street_number
            partner.street2 = location.street2
            partner.city = location.city
            partner.zip = location.zip
            partner.state_id = location.state_id
            partner.country_id = location.country_id

    @api.constrains('location_id', 'parent_id', 'is_company')
    def _check_location_belongs_to_main_company(self):
        for partner in self:
            if not partner.location_id:
                continue

            main_company = partner._get_main_company_for_locations()
            available = main_company.location_ids if main_company else partner.location_ids

            if partner.location_id not in available:
                raise ValidationError(
                    _("La ubicación seleccionada no pertenece a la empresa principal.")
                )

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
            location = partner.location_id

            street_name = partner.street or (location.street if location else False) or (location.name if location else False)
            street_number = partner.street_number or (location.street_number if location else False)

            street_parts = []
            if street_name:
                street_parts.append(street_name)
            if street_number:
                street_parts.append(street_number)
            if partner.city:
                street_parts.append(partner.city)
            if partner.state_id:
                street_parts.append(partner.state_id.name)
            if partner.country_id:
                street_parts.append(partner.country_id.name)

            primary_address = ', '.join([part for part in street_parts if part])
            fallback_address = partner._build_full_address()
            address = primary_address or fallback_address

            if not address or (partner.geocode_address == address and partner.latitude):
                continue

            time.sleep(1)

            params = {
                'format': 'json',
                'limit': 1,
                'addressdetails': 1,
            }

            # Búsqueda estructurada para mayor precisión (evita calles iguales en otras ciudades)
            street_query = ' '.join([part for part in [street_name, street_number] if part]).strip()
            if street_query:
                params['street'] = street_query
            if partner.city:
                params['city'] = partner.city
            if partner.zip:
                params['postalcode'] = partner.zip
            if partner.state_id:
                params['state'] = partner.state_id.name
            if partner.country_id:
                params['country'] = partner.country_id.name
                if partner.country_id.code:
                    params['countrycodes'] = partner.country_id.code.lower()

            # Si faltan datos mínimos para búsqueda estructurada, usar texto libre
            if not params.get('street'):
                params['q'] = address
            headers = {'User-Agent': 'Odoo/CRM Geocode'}

            try:
                resp = requests.get(
                    'https://nominatim.openstreetmap.org/search',
                    params=params,
                    headers=headers,
                    timeout=10,
                )
                data = resp.json() if resp.ok else []

                # Reintento con búsqueda libre si la estructurada no devuelve resultados
                if not data and 'q' not in params and fallback_address:
                    free_params = {
                        'q': fallback_address,
                        'format': 'json',
                        'limit': 1,
                        'addressdetails': 1,
                    }
                    if partner.country_id and partner.country_id.code:
                        free_params['countrycodes'] = partner.country_id.code.lower()
                    resp = requests.get(
                        'https://nominatim.openstreetmap.org/search',
                        params=free_params,
                        headers=headers,
                        timeout=10,
                    )
                    data = resp.json() if resp.ok else []
                    if data:
                        address = fallback_address

                if not data and fallback_address and fallback_address != address:
                    fallback_params = {
                        'q': fallback_address,
                        'format': 'json',
                        'limit': 1,
                        'addressdetails': 1,
                    }
                    resp = requests.get(
                        'https://nominatim.openstreetmap.org/search',
                        params=fallback_params,
                        headers=headers,
                        timeout=10,
                    )
                    data = resp.json() if resp.ok else []
                    if data:
                        address = fallback_address

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

    @api.depends('child_ids', 'child_ids.type', 'child_ids.is_company')
    def _compute_contact_count(self):
        for partner in self:
            if partner.is_company:
                partner.contact_count = len(partner.child_ids.filtered(lambda c: not c.is_company and c.type == 'contact'))
            else:
                partner.contact_count = 0

    def action_view_contacts(self):
        self.ensure_one()
        return {
            'name': f'Contactos de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id), ('type', '=', 'contact'), ('is_company', '=', False)],
            'context': {
                'default_parent_id': self.id,
                'default_type': 'contact',
                'default_is_company': False,
            },
        }
#
#    @api.constrains('lopd_signed', 'lopd_document_id')
#    def _check_lopd_document(self):
#        for partner in self:
#            if partner.lopd_signed and not partner.lopd_document_id:
#                raise ValidationError(
#                    _("Si marca la LOPD como firmada, debe importar el documento mediante el botón 'Importar documento LOPD'.")
#                )

    @api.constrains('billing_sepa_signed', 'billing_sepa_document_id')
    def _check_billing_sepa_document(self):
        if self.env.context.get('import_file'):
            return
        for partner in self:
            if partner.billing_sepa_signed and not partner.billing_sepa_document_id:
                raise ValidationError(
                    _("Si marca SEPA como firmado, debe adjuntar el documento mediante el botón 'Adjuntar documento SEPA'.")
                )

    @api.constrains('vat', 'country_id')
    def check_vat(self):
        if self.env.context.get('import_file'):
            return
        return super().check_vat()

    def _sanitize_import_vat(self, vat_value, country_id):
        if not vat_value or not country_id:
            return vat_value
        country = self.env['res.country'].browse(country_id)
        if country.code != 'ES':
            return vat_value
        compact_vat = ''.join(char for char in vat_value.upper() if char.isalnum())
        if not compact_vat:
            return vat_value
        return compact_vat if compact_vat.startswith('ES') else f'ES{compact_vat}'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('vat') and self.env.context.get('import_file'):
                country_id = vals.get('country_id')
                vals['vat'] = self._sanitize_import_vat(vals['vat'], country_id)
            is_company = vals.get('is_company', False)
            if not is_company:
                vals.setdefault('type', 'contact')
                first = (vals.get('first_name') or '').strip()
                last = (vals.get('last_name') or '').strip()
                if first or last:
                    vals['name'] = ' '.join(p for p in [first, last] if p)
            else:
                vals.setdefault('type', 'other')
        partners = super().create(vals_list)
        partners.filtered(lambda partner: partner.is_company)._ensure_contract_option_lines()
        return partners

    def write(self, vals):
        if vals.get('vat') and self.env.context.get('import_file') and len(self) > 1:
            for partner in self:
                partner_vals = dict(vals)
                country_id = partner_vals.get('country_id', partner.country_id.id)
                partner_vals['vat'] = self._sanitize_import_vat(partner_vals['vat'], country_id)
                super(Partner, partner).write(partner_vals)
            return True

        if vals.get('vat') and self.env.context.get('import_file') and len(self) == 1:
            country_id = vals.get('country_id', self.country_id.id)
            vals['vat'] = self._sanitize_import_vat(vals['vat'], country_id)

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

        result = super().write(vals)
        self.filtered(lambda partner: partner.is_company)._ensure_contract_option_lines()
        return result

    def _ensure_contract_option_lines(self):
        companies = self.filtered(lambda partner: partner.is_company)
        if not companies:
            return

        options = self.env['crm.contract.option'].search([('active', '=', True)])
        if not options:
            return

        line_model = self.env['crm.contract.option.line']
        lines_to_create = []

        for company in companies:
            existing_option_ids = set(company.contract_extra_line_ids.mapped('option_id').ids)
            selected_option_ids = set(company.contract_extra_option_ids.ids)
            missing_options = options.filtered(lambda option: option.id not in existing_option_ids)

            for option in missing_options:
                lines_to_create.append({
                    'partner_id': company.id,
                    'option_id': option.id,
                    'enabled': option.id in selected_option_ids,
                })

        if lines_to_create:
            line_model.create(lines_to_create)

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('street') and vals.get('name'):
                vals['street'] = vals['name'].strip()
        return super().create(vals_list)

    def write(self, vals):
        if not vals.get('street') and vals.get('name'):
            vals = dict(vals)
            vals['street'] = vals['name'].strip()
        return super().write(vals)

    def name_get(self):
        result = []
        for location in self:
            label_parts = []
            if location.name:
                label_parts.append(location.name)

            street_parts = []
            if location.street:
                street = location.street
                if location.street_number:
                    street = f"{street} {location.street_number}".strip()
                street_parts.append(street)
            elif location.street_number:
                street_parts.append(location.street_number)

            if location.city:
                street_parts.append(location.city)

            if street_parts:
                label_parts.append(" - ".join([street_parts[0], ", ".join(street_parts[1:])]).strip(" -"))

            label = " | ".join([part for part in label_parts if part]) or _("Sin ubicación")
            result.append((location.id, label))
        return result

    def _build_full_address(self):
        self.ensure_one()
        parts = []

        street_value = self.street or self.name
        if street_value:
            street_part = street_value
            if self.street_number:
                street_part = f"{street_value}, {self.street_number}"
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


class CrmContractOption(models.Model):
    _name = 'crm.contract.option'
    _description = 'Contrato adicional de cuenta'
    _order = 'sequence, name, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Contrato', required=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        options = super().create(vals_list)
        companies = self.env['res.partner'].search([('is_company', '=', True)])
        if not companies:
            return options

        line_model = self.env['crm.contract.option.line']
        lines_to_create = []
        for company in companies:
            existing_option_ids = set(company.contract_extra_line_ids.mapped('option_id').ids)
            for option in options:
                if option.id not in existing_option_ids:
                    lines_to_create.append({
                        'partner_id': company.id,
                        'option_id': option.id,
                        'enabled': False,
                    })

        if lines_to_create:
            line_model.create(lines_to_create)

        return options


class CrmContractOptionLine(models.Model):
    _name = 'crm.contract.option.line'
    _description = 'Contrato adicional por cuenta'
    _order = 'option_id'

    partner_id = fields.Many2one('res.partner', string='Cuenta', required=True, ondelete='cascade')
    option_id = fields.Many2one('crm.contract.option', string='Contrato', required=True, ondelete='cascade')
    enabled = fields.Boolean(string='Activo', default=False)

    _sql_constraints = [
        ('crm_contract_option_line_unique', 'unique(partner_id, option_id)', 'El contrato ya existe en esta cuenta.'),
    ]


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
