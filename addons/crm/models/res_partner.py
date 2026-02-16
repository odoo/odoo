<<<<<<< HEAD
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression
=======
import requests
import time
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
>>>>>>> 5ec06c51f0d1 (update contactos y cuentas)


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    centralita_number = fields.Char(
        string="Número de Centralita",
    )
    trade_name = fields.Char(
        string="Marca Comercial",
        help="Nombre comercial de la empresa"
    )
    fax = fields.Char(
        string="Fax",
    )
    def _selection_relationship_type(self):
        types = self.env["crm.relationship.type"].search([
            ("active", "=", True),
        ], order="sequence, name")
        return [(rel_type.code, rel_type.name) for rel_type in types]

    relationship_type = fields.Selection(
        selection=_selection_relationship_type,
        string="Tipo de relación",
    )
    lopd_signed = fields.Boolean(
        string="LOPD firmada",
        default=False
    )
    lopd_document_id = fields.Many2one(
        'ir.attachment',
        string="Documento LOPD",
        help="Archivo PDF o documento de la LOPD firmada"
    )
    notes = fields.Text(
        string="Notas",
    )
    contact_count = fields.Integer(
        string="Número de Contactos",
        compute='_compute_contact_count',
    )
    
    # Campos de mensajes Outlook
    outlook_message_count = fields.Integer(
        string='Mensajes Outlook',
        compute='_compute_outlook_message_count'
    )

<<<<<<< HEAD
    def _compute_opportunity_count(self):
        self.opportunity_count = 0
        if not self.env.user._has_group('sales_team.group_sale_salesman'):
            return

        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)], ['parent_id'],
        )

        opportunity_data = self.env['crm.lead'].with_context(active_test=False)._read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            groupby=['partner_id'], aggregates=['__count']
        )
        self_ids = set(self._ids)

        for partner, count in opportunity_data:
            while partner:
                if partner.id in self_ids:
                    partner.opportunity_count += count
                partner = partner.parent_id

    def action_view_opportunity(self):
        '''
        This function returns an action that displays the opportunities from partner.
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_opportunities')
        action['context'] = {}
        if self.is_company:
            action['domain'] = [('partner_id.commercial_partner_id', '=', self.id)]
        else:
            action['domain'] = [('partner_id', '=', self.id)]
        action['domain'] = expression.AND([action['domain'], [('active', 'in', [True, False])]])
        return action
=======
    # Campos de Contratos
    contract_it_bonus = fields.Boolean(string="Bono informática", default=False)
    contract_total_it_maintenance = fields.Boolean(string="Mantenimiento total informática", default=False)
    contract_physical_centralita = fields.Boolean(string="Mantenimiento centralita física", default=False)
    contract_cloud_centralita = fields.Boolean(string="Mantenimiento centralita cloud", default=False)
    contract_vpn = fields.Boolean(string="Mantenimiento VPN", default=False)
    contract_acronis = fields.Boolean(string="Acronis", default=False)
    contract_antivirus = fields.Boolean(string="Antivirus", default=False)
    contract_office365 = fields.Boolean(string="Office 365", default=False)
    contract_incidents_cobro = fields.Boolean(string="Incidencias cobro", default=False)
    
    # Campos de Dirección
    street_number = fields.Char(
        string="Número",
        help="Número de la calle"
    )
    
    # Campos de Geolocalización
    latitude = fields.Float(
        string="Latitud",
        digits=(10, 8),
        help="Latitud de la ubicación"
    )
    longitude = fields.Float(
        string="Longitud",
        digits=(10, 8),
        help="Longitud de la ubicación"
    )
    geocode_address = fields.Char(
        string="Dirección geocodificada",
        readonly=True,
        help="Última dirección usada para geocodificar"
    )
    last_geocode = fields.Datetime(
        string="Última geocodificación",
        readonly=True,
        help="Fecha y hora de la última geocodificación"
    )
    map_html = fields.Html(
        string="Mapa",
        compute='_compute_map_html',
        sanitize=False,
        help="Mapa con la ubicación de la dirección"
    )

    @api.depends('latitude', 'longitude')
    def _compute_map_html(self):
        """Genera HTML con mapa OSM embebido"""
        for partner in self:
            if partner.latitude and partner.longitude:
                zoom = 15
                lat = partner.latitude
                lon = partner.longitude
                # Crear coordenadas boundind box para el iframe
                bbox_margin = 0.01
                bbox = f"{lon-bbox_margin},{lat-bbox_margin},{lon+bbox_margin},{lat+bbox_margin}"
                
                partner.map_html = f'''
                <div style="width: 100%; height: 400px; border-radius: 4px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.12);">
                    <iframe width="100%" height="100%" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" 
                        src="https://www.openstreetmap.org/export/embed.html?bbox={bbox}&amp;layer=mapnik&amp;marker={lat},{lon}"
                        style="border: 0; width: 100%; height: 100%;">
                    </iframe>
                </div>
                '''
            else:
                partner.map_html = '<div style="padding: 20px; text-align: center; color: #999; background: #f9f9f9; border-radius: 4px; border: 1px dashed #ddd;"><p>Selecciona una dirección para ver el mapa</p></div>'

    def _build_full_address(self):
        """Construye una dirección completa para geocodificación"""
        self.ensure_one()
        parts = []

        # Construir calle con número
        if self.street:
            street_part = self.street
            if self.street_number:
                street_part = f"{self.street}, {self.street_number}"
            parts.append(street_part)
        
        # Añadir el resto de componentes
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
        
        return ", ".join(parts)

    def action_geocode_address(self):
        import logging
        _logger = logging.getLogger(__name__)
        
        for partner in self:
            address = partner._build_full_address()
            
            # Si no hay dirección o ya está geocodificada con la misma dirección, saltar
            if not address or (partner.geocode_address == address and partner.latitude):
                continue

            # Respetar límite de 1 petición/segundo
            time.sleep(1)
            
            params = {
                "q": address,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            }
            headers = {"User-Agent": "Odoo/CRM Geocode"}
            
            try:
                resp = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params=params,
                    headers=headers,
                    timeout=10,
                )
                data = resp.json() if resp.ok else []
                
                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    partner.write({
                        "latitude": lat,
                        "longitude": lon,
                        "last_geocode": fields.Datetime.now(),
                        "geocode_address": address,
                    })
                    _logger.info(f"Geocodificación exitosa para {partner.name}: {lat}, {lon}")
            except Exception as e:
                _logger.warning(f"Error geocodificando dirección para {partner.name}: {e}")

    @api.model
    def action_reverse_geocode(self, lat, lon):
        """Devuelve dirección en base a coordenadas"""
        import logging
        _logger = logging.getLogger(__name__)
        
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1,
        }
        headers = {"User-Agent": "Odoo/CRM Reverse Geocode"}
        
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params=params,
                headers=headers,
                timeout=10,
            )
            data = resp.json() if resp.ok else {}
            addr = data.get("address", {})

            country = self.env["res.country"].search(
                [("code", "=", (addr.get("country_code") or "").upper())],
                limit=1
            )
            state = self.env["res.country.state"].search(
                [("name", "ilike", addr.get("state", "")), ("country_id", "=", country.id)],
                limit=1
            ) if country else None
            
            city_name = addr.get("city") or addr.get("town") or addr.get("village")
            
            # Intentar buscar ciudad en res.city si está disponible
            city = False
            if city_name and state:
                city = self.env["res.city"].search(
                    [("name", "ilike", city_name), ("state_id", "=", state.id)],
                    limit=1
                )

            result = {
                "street": addr.get("road") or "",
                "street_number": addr.get("house_number") or "",
                "street2": "",
                "zip": addr.get("postcode") or "",
                "city": city_name or "",
                "state_id": state.id if state else False,
                "country_id": country.id if country else False,
            }
            
            # Agregar city_id solo si existe el campo y se encontró la ciudad
            if city:
                result["city_id"] = city.id
                
            return result
        except Exception as e:
            _logger.warning(f"Error en reverse geocode: {e}")
            return {}

    def action_view_on_map(self):
        """Abrir OpenStreetMap en una nueva pestaña con la ubicación del partner"""
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
                }
            }
        
        zoom = 15
        url = f"https://www.openstreetmap.org/?mlat={self.latitude}&mlon={self.longitude}&zoom={zoom}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def _compute_outlook_message_count(self):
        """Cuenta los mensajes enviados desde Outlook"""
        for partner in self:
            partner.outlook_message_count = self.env['mail.message'].search_count([
                ('res_id', '=', partner.id),
                ('model', '=', 'res.partner'),
                ('message_type', '=', 'email')
            ])
    
    def action_send_outlook_message(self):
        """Abre el asistente para enviar mensaje por Outlook"""
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
        """Ver todos los mensajes de Outlook de este contacto"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mensajes de Outlook'),
            'res_model': 'mail.message',
            'view_mode': 'tree,form',
            'domain': [
                ('res_id', '=', self.id),
                ('model', '=', 'res.partner'),
                ('message_type', '=', 'email')
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
        """Valida que si LOPD está firmada, debe haber un documento importado"""
        for partner in self:
            if partner.lopd_signed and not partner.lopd_document_id:
                raise ValidationError(
                    _("Si marca la LOPD como firmada, debe importar el documento mediante el botón 'Importar documento LOPD'.")
                )

    @api.model
    def create(self, vals):
        if vals.get('is_company') is False and not vals.get('type'):
            vals['type'] = 'contact'
        return super().create(vals)

    @api.onchange('is_company')
    def _onchange_is_company(self):
        if self.is_company:
            self.type = 'contact'
        else:
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
                'default_name': f'LOPD_{self.name}',
            },
        }
class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        """Al crear un attachment desde importación LOPD, vincularlo al partner"""
        attachments = super().create(vals_list)
        
        # Si es una importación de LOPD, vincular al partner
        if self.env.context.get('lopd_import') and self.env.context.get('partner_id'):
            partner_id = self.env.context.get('partner_id')
            partner = self.env['res.partner'].browse(partner_id)
            
            # Vincular el primer attachment creado al campo lopd_document_id
            if attachments and partner.exists():
                partner.write({'lopd_document_id': attachments[0].id})
        
        return attachments
>>>>>>> 5ec06c51f0d1 (update contactos y cuentas)
