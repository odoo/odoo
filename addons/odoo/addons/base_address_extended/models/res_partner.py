# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
import requests
import logging

_logger = logging.getLogger(__name__)

class Partner(models.Model):
    _inherit = ['res.partner']

    street_name = fields.Char(
        'Street Name', compute='_compute_street_data', inverse='_inverse_street_data', store=True)
    street_number = fields.Char(
        'House', compute='_compute_street_data', inverse='_inverse_street_data', store=True)
    street_number2 = fields.Char(
        'Door', compute='_compute_street_data', inverse='_inverse_street_data', store=True)

    city_id = fields.Many2one(comodel_name='res.city', string='City ID')
    country_enforce_cities = fields.Boolean(related='country_id.enforce_cities')

    @api.model
    def _address_fields(self):
        return super()._address_fields() + ['city_id']

    def _inverse_street_data(self):
        """ update self.street based on street_name, street_number and street_number2 """
        for partner in self:
            street = ((partner.street_name or '') + " " + (partner.street_number or '')).strip()
            if partner.street_number2:
                street = street + " - " + partner.street_number2
            partner.street = street

    @api.depends('street')
    def _compute_street_data(self):
        """Splits street value into sub-fields.
        Recomputes the fields of STREET_FIELDS when `street` of a partner is updated"""
        for partner in self:
            partner.update(tools.street_split(partner.street))

    def _get_street_split(self):
        self.ensure_one()
        return {
            'street_name': self.street_name,
            'street_number': self.street_number,
            'street_number2': self.street_number2
        }

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            self.zip = self.city_id.zipcode
            self.state_id = self.city_id.state_id
        elif self._origin:
            self.city = False
            self.zip = False
            self.state_id = False

    @api.onchange('country_id')
    def _onchange_country_id(self):
        super()._onchange_country_id()
        if self.country_id and self.country_id != self.city_id.country_id:
            self.city_id = False

    # ==================== CAMPOS Y MÉTODOS DEL MAPA ====================

    partner_latitude = fields.Float(
        string="Latitud",
        digits=(10, 8),
        help="Latitud de la ubicación del socio para mostrar en el mapa"
    )
    partner_longitude = fields.Float(
        string="Longitud",
        digits=(10, 8),
        help="Longitud de la ubicación del socio para mostrar en el mapa"
    )
    map_url = fields.Char(
        string="URL del Mapa",
        compute='_compute_map_url',
        help="URL para abrir la ubicación en OpenStreetMap"
    )
    last_geocode = fields.Datetime(
        string="Última geocodificación",
        readonly=True,
        help="Fecha y hora del último geocoding realizado"
    )

    @api.depends('partner_latitude', 'partner_longitude')
    def _compute_map_url(self):
        """Genera URL para abrir en OpenStreetMap"""
        for partner in self:
            if partner.partner_latitude and partner.partner_longitude:
                partner.map_url = f"https://www.openstreetmap.org/?mlat={partner.partner_latitude}&mlon={partner.partner_longitude}&zoom=15"
            else:
                partner.map_url = ""

    @api.onchange('street', 'city', 'state_id', 'country_id', 'zip')
    def _onchange_address_geocode(self):
        """Auto-geocodificar cuando cambia la dirección"""
        if self.street and self.city and self.country_id:
            # Solo geocodificar si el partner ya existe
            if self.id:
                self._geocode_address()

    def _geocode_address(self):
        """Obtener coordenadas de OpenStreetMap Nominatim"""
        try:
            address_parts = []
            if self.street:
                address_parts.append(self.street)
            if self.city:
                address_parts.append(self.city)
            if self.state_id:
                address_parts.append(self.state_id.name)
            if self.country_id:
                address_parts.append(self.country_id.name)
            if self.zip:
                address_parts.append(self.zip)

            full_address = ", ".join(address_parts)
            
            # Realizar petición a Nominatim
            response = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params={
                    'q': full_address,
                    'format': 'json',
                    'limit': 1
                },
                timeout=5,
                headers={'User-Agent': 'Odoo-Partner-Map/1.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    geo_data = data[0]
                    self.partner_latitude = float(geo_data.get('lat', 0))
                    self.partner_longitude = float(geo_data.get('lon', 0))
                    self.last_geocode = fields.Datetime.now()
                    _logger.info(
                        f"Partner {self.name}: Geocoded to {self.partner_latitude}, {self.partner_longitude}"
                    )
                else:
                    _logger.warning(f"Partner {self.name}: Could not geocode address: {full_address}")
            else:
                _logger.error(
                    f"Partner {self.name}: Nominatim response error {response.status_code}"
                )
                
        except requests.exceptions.Timeout:
            _logger.warning(f"Partner {self.name}: Geocoding timeout for address: {self.street}, {self.city}")
        except requests.exceptions.ConnectionError:
            _logger.warning(f"Partner {self.name}: Could not connect to Nominatim service")
        except Exception as e:
            _logger.error(f"Partner {self.name}: Geocoding error: {str(e)}")

    def action_view_on_map(self):
        """Acción para ver el socio en el mapa de OpenStreetMap"""
        self.ensure_one()
        if self.partner_latitude and self.partner_longitude:
            return {
                'type': 'ir.actions.act_url',
                'url': self.map_url,
                'target': 'new',
            }
        else:
            raise ValueError(
                f"Partner {self.name} no tiene coordenadas disponibles. "
                "Asegúrate de que la dirección esté completa y la geocodificación haya sido realizada."
            )

    def button_geocode_all_partners(self):
        """Botón para geocodificar todos los partners existentes"""
        partners = self.search([
            '|',
            ('partner_latitude', '=', 0),
            ('partner_latitude', '=', False),
        ])
        
        count = 0
        for partner in partners:
            if partner.street and partner.city:
                try:
                    partner._geocode_address()
                    count += 1
                except Exception as e:
                    _logger.error(f"Error geocoding partner {partner.name}: {str(e)}")
        
        _logger.info(f"Geocoded {count} partners successfully")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Geocodificación completada',
                'message': f'Se geocodificaron {count} socios comerciales exitosamente.',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def create(self, vals):
        """Override create para geocodificar al crear un partner"""
        record = super().create(vals)
        if record.street and record.city:
            try:
                record._geocode_address()
            except Exception as e:
                _logger.warning(f"Could not geocode new partner {record.name}: {str(e)}")
        return record

    def write(self, vals):
        """Override write para geocodificar al actualizar dirección"""
        result = super().write(vals)
        
        # Verificar si alguno de los campos de dirección fue actualizado
        address_fields = {'street', 'city', 'state_id', 'country_id', 'zip'}
        if any(field in vals for field in address_fields):
            for partner in self:
                if partner.street and partner.city:
                    try:
                        partner._geocode_address()
                    except Exception as e:
                        _logger.warning(f"Could not geocode partner {partner.name}: {str(e)}")
        
        return result

