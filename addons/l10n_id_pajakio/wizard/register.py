# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import logging
from odoo import _, fields, models
from odoo.addons.l10n_id_pajakio.const import PAJAKIO_URL
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class RegisterUserPajakIO(models.TransientModel):
    """
    In Pajak.io, there are 2 levels of uses: user-level and company-level.
    Once a user is registered, only then they can register a company under the user.
    """
    _name = 'l10n_id_pajakio.register.user'
    _description = 'Register User PajakIO'

    email = fields.Char(string='Email', required=True, help="Email used to register on Pajak.io")
    password = fields.Char(string='Password', required=True, help="Password used to register on Pajak.io")
    name = fields.Char(string='Name', required=True, help="Name of the user")
    phone = fields.Char(string='Phone', required=True, help="Phone number of the user")

    def action_register(self):
        """ API call for user registration """
        mode = self.env['ir.config_parameter'].sudo().get_param('l10n_id_pajakio.mode')
        base_url = PAJAKIO_URL.get(mode)
        url = f"{base_url}/register-user"

        payload = {
            "email": self.email,
            "nama": self.name,
            "telp": self.phone,
            "password": self.password,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ValidationError(_("Pajak.io: Could not establish a connection to Pajak.io API"))
        except requests.exceptions.HTTPError as err:
            err_response = err.response.json()
            err_message = err_response.get('message', 'Unknown error')
            _logger.error("Paja.io: User registration failed, response: %s", err_response)
            raise ValidationError(_("Pajak.io: Communication with API failed. Pajak.io returned the following: '%s'", err_message))

        # if everything goes well during user registration, user still needs tos register further for the company,
        # carry the email and password info to the next popup
        res = response.json()
        _logger.info("Pajak.io: User registration successful, response: %s", res)

        if mode == "test":
            self.env['ir.config_parameter'].sudo().set_param("l10n_id_pajakio.test_email", self.email)
            self.env['ir.config_parameter'].sudo().set_param("l10n_id_pajakio.test_password", self.password)
        else:
            self.env['ir.config_parameter'].sudo().set_param("l10n_id_pajakio.email", self.email)
            self.env['ir.config_parameter'].sudo().set_param("l10n_id_pajakio.password", self.password)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_id_pajakio.register.company',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_email': self.email,
                'default_password': self.password,
                'default_npwp': self.env.company.vat or '',
            }
        }


class RegisterCompanyPajakIO(models.TransientModel):
    _name = 'l10n_id_pajakio.register.company'
    _description = 'Register Company PajakIO'

    # Fields required for company registration where email and password are carried from the previous user registration
    email = fields.Char(string='Email', required=True, help="Email used to register on Pajak.io")
    password = fields.Char(string='Password', required=True, help="Password used to register on Pajak.io")
    company_name = fields.Char(string='Company Name', required=True, help="Registered name of the company")
    npwp = fields.Char(string='NPWP', required=True, help="NPWP of the company")
    address = fields.Char(string='Address', required=True, help="Address of the company")
    city = fields.Char(string='City', required=True, help="City where the company is located")
    
    def action_register(self):
        """ Invoke API call for company registration """
        mode = self.env['ir.config_parameter'].sudo().get_param('l10n_id_pajakio.mode')
        base_url = PAJAKIO_URL.get(mode)
        url = f"{base_url}/register-company"

        payload = {
            "email": self.email,
            "password": self.password,
            "nama": self.company_name,
            "npwp": self.npwp,
            "alamat": self.address,
            "kota": self.city,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ValidationError(_("Pajak.io: Could not establish a connection to Pajak.io API"))
        except requests.exceptions.HTTPError as err:
            err_response = err.response.json()
            err_message = err_response.get('message', 'Unknown error')
            raise ValidationError(_("Pajak.io: Communication with API failed. Pajak.io returned the following: '%s", err_message))

        # if it's process correctly, we will store clientId
        res = response.json()
        _logger.info("Pajak.io: Company registration successful, response: %s", res)
        client_id = res.get('data', {}).get('clientId')
        if mode == "test":
            self.env['ir.config_parameter'].sudo().set_param("l10n_id_pajakio.test_client_id", client_id)
        else:
            self.env['ir.config_parameter'].sudo().set_param("l10n_id_pajakio.client_id", client_id)


class SignIn(models.TransientModel):
    _name = "l10n_id_pajakio.signin"
    _description = "Sign In Pajak.io"

    email = fields.Char(string='Email', required=True, help="Email used to register on Pajak.io")
    password = fields.Char(string='Password', required=True, help="Password used to register on Pajak.io")
    npwp = fields.Char(string="NPWP", required=True, help="NPWP of the company")

    def action_sign_in(self):
        """ Call get-client-id API in order to get the client ID of a particular user account """
        mode = self.env['ir.config_parameter'].sudo().get_param('l10n_id_pajakio.mode')
        base_url = PAJAKIO_URL.get(mode)
        url = f"{base_url}/get-client-id"

        payload = {
            "email": self.email,
            "password": self.password,
            "npwp": self.npwp,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ValidationError(_("Pajak.io: Could not establish a connection to Pajak.io API"))
        except requests.exceptions.HTTPError as err:
            err_response = err.response.json()
            err_message = err_response.get('message', 'Unknown error')
            raise ValidationError(_("Pajak.io: Communication with API failed. Pajak.io returned the following: '%s", err_message))

        res = response.json()
        _logger.info("Pajak.io: Sign in successful, response: %s", res)
        client_id = res.get('data', {}).get('clientId')
        
        # email and password no need to be stored
        if mode == "test":
            self.env['ir.config_parameter'].sudo().set_param("l10n_id_pajakio.test_client_id", client_id)
        else:
            self.env['ir.config_parameter'].sudo().set_param("l10n_id_pajakio.client_id", client_id)
