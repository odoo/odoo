# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models



class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('name')
    def _onchange_name_autofill_address(self):
        """
        Autocompleta los campos de dirección usando la API de OSM (Nominatim) al escribir el nombre de la ubicación.
        """
        import requests
        if self.name:
            try:
                url = "https://nominatim.openstreetmap.org/search"
                params = {
                    'q': self.name,
                    'format': 'json',
                    'addressdetails': 1,
                    'limit': 1,
                }
                headers = {
                    'User-Agent': 'Odoo-Autocomplete/1.0'
                }
                response = requests.get(url, params=params, headers=headers, timeout=3)
                if response.status_code == 200:
                    results = response.json()
                    if results:
                        address = results[0].get('address', {})
                        self.street = address.get('road') or ''
                        if hasattr(self, 'street_number'):
                            self.street_number = address.get('house_number') or ''
                        self.city = address.get('city') or address.get('town') or address.get('village') or ''
                        self.zip = address.get('postcode') or ''
                        # Buscar país y provincia en la base de datos de Odoo
                        country_name = address.get('country')
                        state_name = address.get('state')
                        if country_name:
                            country = self.env['res.country'].search([('name', 'ilike', country_name)], limit=1)
                            if country:
                                self.country_id = country.id
                        if state_name:
                            state = self.env['res.country.state'].search([('name', 'ilike', state_name)], limit=1)
                            if state:
                                self.state_id = state.id
            except Exception as e:
                # Si hay error, no autocompleta
                pass

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('contacts.menu_contacts').id]
        
        
    