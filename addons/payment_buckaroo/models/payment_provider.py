# Part of Odoo. See LICENSE file for full copyright and licensing details.

from hashlib import sha1

from werkzeug import urls

from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('buckaroo', "Buckaroo")], ondelete={'buckaroo': 'set default'})
    buckaroo_website_key = fields.Char(
        string="Website Key", help="The key solely used to identify the website with Buckaroo",
        required_if_provider='buckaroo')
    buckaroo_secret_key = fields.Char(
        string="Buckaroo Secret Key", required_if_provider='buckaroo', groups='base.group_system')

    def _buckaroo_get_api_url(self):
        """ Return the API URL according to the state.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()
        if self.state == 'enabled':
            return 'https://checkout.buckaroo.nl/html/'
        else:
            return 'https://testcheckout.buckaroo.nl/html/'

    def _buckaroo_generate_digital_sign(self, values, incoming=True):
        """ Generate the shasign for incoming or outgoing communications.

        :param dict values: The values used to generate the signature
        :param bool incoming: Whether the signature must be generated for an incoming (Buckaroo to
                              Odoo) or outgoing (Odoo to Buckaroo) communication.
        :return: The shasign
        :rtype: str
        """
        if incoming:
            # Incoming communication values must be URL-decoded before checking the signature. The
            # key 'brq_signature' must be ignored.
            items = [
                (k, urls.url_unquote_plus(v)) for k, v in values.items()
                if k.lower() != 'brq_signature'
            ]
        else:
            items = values.items()
        # Only use items whose key starts with 'add_', 'brq_', or 'cust_' (case insensitive)
        filtered_items = [
            (k, v) for k, v in items
            if any(k.lower().startswith(key_prefix) for key_prefix in ('add_', 'brq_', 'cust_'))
        ]
        # Sort parameters by lower-cased key. Not upper-case because ord('A') < ord('_') < ord('a').
        sorted_items = sorted(filtered_items, key=lambda pair: pair[0].lower())
        # Build the signing string by concatenating all parameters
        sign_string = ''.join(f'{k}={v or ""}' for k, v in sorted_items)
        # Append the pre-shared secret key to the signing string
        sign_string += self.buckaroo_secret_key
        # Calculate the SHA-1 hash over the signing string
        return sha1(sign_string.encode('utf-8')).hexdigest()
