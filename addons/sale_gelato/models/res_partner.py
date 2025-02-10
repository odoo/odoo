# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.payment import utils as payment_utils


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _gelato_prepare_address_payload(self):
        first_name, last_name = payment_utils.split_partner_name(self.name)
        return {
            'companyName': self.commercial_company_name or '',
            'firstName': first_name or last_name,  # Gelato require a first name.
            'lastName': last_name,
            'addressLine1': self.street,
            'addressLine2': self.street2 or '',
            'state': self.state_id.code,
            'city': self.city,
            'postCode': self.zip,
            'country': self.country_id.code,
            'email': self.email,
            'phone': self.phone or ''
        }
