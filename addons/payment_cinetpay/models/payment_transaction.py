from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import hmac
import hashlib
import requests
import logging

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """Prépare les données à envoyer à l'API CinetPay pour initier la transaction."""
        self.ensure_one()

        provider = self.provider_id
        if provider.code != 'cinetpay':
            return super()._get_specific_rendering_values(processing_values)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        notify_url = f"{base_url}/payment/cinetpay/ipn"
        return_url = self.get_return_url()

        # Récupération des informations détaillées du client
        customer = self.partner_id
        customer_phone_number = customer.phone or ""
        customer_address = customer.street or ""
        customer_city = customer.city or ""
        customer_country = customer.country_id.code or ""
        customer_state = customer.state_id.code or ""
        customer_zip_code = customer.zip or ""

        # Construction de la requête à envoyer à CinetPay
        payload = {
            'apikey': provider.cinetpay_api_key,
            'site_id': provider.cinetpay_site_id,
            'transaction_id': self.reference,  # Ou générer un ID unique ici
            'amount': str(self.amount),
            'currency': self.currency_id.name,
            'description': self.reference,
            'return_url': return_url,
            'notify_url': notify_url,
            'customer_id': str(customer.id),  # Identifiant unique du client (optionnel)
            'customer_name': customer.name,
            'customer_email': customer.email or 'noemail@example.com',
            'customer_phone_number': customer_phone_number,
            'customer_address': customer_address,
            'customer_city': customer_city,
            'customer_country': customer_country,
            'customer_state': customer_state,
            'customer_zip_code': customer_zip_code,
            'channels': 'ALL',  # Optionnel, peut être personnalisé selon ton besoin
            'metadata': 'user1',  # Optionnel
            'lang': 'FR',  # Langue à afficher pendant le paiement
            'invoice_data': {
                'Donnee1': '',  # Remplir ces champs si nécessaire
                'Donnee2': '',
                'Donnee3': ''
            }
        }

        _logger.info("CinetPay: Préparation de la transaction : %s", payload)

        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post("https://api-checkout.cinetpay.com/v2/payment", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get('code') != '201':
                raise ValidationError(_('Erreur CinetPay: %s') % data.get('message'))

            return {
                'api_url': data['data']['payment_url'],
            }

        except requests.RequestException as e:
            _logger.error("Erreur lors de l'appel à l'API CinetPay : %s", e)
            raise ValidationError(_("Une erreur est survenue lors de la connexion à CinetPay."))
