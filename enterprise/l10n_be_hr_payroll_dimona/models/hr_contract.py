# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import jwt
import re
import secrets
import string
import time

from datetime import timedelta
from werkzeug.urls import url_quote
from requests import request
from requests.exceptions import HTTPError

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import file_open


API_DATA = json.loads(file_open('l10n_be_hr_payroll_dimona/data/api_data.json').read())
API_ROUTES = API_DATA['routes']['production']
DIMONA_TIMEOUT = 30


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_be_dimona_in_declaration_number = fields.Char(groups="hr_payroll.group_hr_payroll_user")
    l10n_be_dimona_last_declaration_number = fields.Char(groups="hr_payroll.group_hr_payroll_user")
    l10n_be_dimona_declaration_state = fields.Selection(
        selection=[
            ('none', 'Not Declared'),
            ('waiting', 'Declared and waiting status'),
            ('done', 'Declared and accepted'),
            ('done_warning', 'Declared and accepted with warnings'),
            ('refused', 'Declared and refused'),
            ('waiting_sigedis', 'Declared and waiting Sigedis'),
            ('error', "Invalid declaration or restricted access"),
        ], default='none')
    l10n_be_dimona_planned_hours = fields.Integer("Student Planned Hours")
    l10n_be_is_student = fields.Boolean(compute='_compute_l10n_be_is_student')

    @api.depends('structure_type_id')
    def _compute_l10n_be_is_student(self):
        student_stuct_type = self.env.ref('l10n_be_hr_payroll.structure_type_student')
        for contract in self:
            contract.l10n_be_is_student = contract.structure_type_id == student_stuct_type

    def _validate_response(self, key, response):
        response_json = response.json()
        expected_format = API_DATA['response_validation'][key]['response']
        if response.status_code != API_DATA['response_validation'][key]['status']:
            return response_json
        if len(response_json) != len(expected_format):
            raise UserError(_(' The API response is not in the expected format. Please contact an administrator.'))
        for field, field_type in expected_format.items():
            if field not in response_json:
                raise UserError(_(' The API response is not containing the required fields. Please contact an administrator.'))
            if not isinstance(response_json[field], field_type):
                raise UserError(_(' The API response have an unexpected type. Please contact an administrator.'))
        return response_json

    def _get_jwt(self):
        expeditor_number = self.company_id.onss_expeditor_number
        if not expeditor_number:
            raise UserError(_('No expeditor number defined on the payroll settings.'))
        certificate_sudo = self.company_id.sudo().onss_certificate_id
        if not certificate_sudo:
            raise UserError(_('No Certificate definer on the Payroll Configuration'))
        unique_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20))
        now = int(time.time())
        payload = {
            # Unique jwt indentifier
            "jti": unique_id,
            # App supplying the jwt
            "iss": API_DATA['jwt']['user'] % (self.company_id.onss_expeditor_number),
            # Main jwt subject
            "sub": API_DATA['jwt']['user'] % (self.company_id.onss_expeditor_number),
            # jwt receiver (audience)
            "aud": API_DATA['jwt']['audiance'],
            # Expiration
            "exp": now + API_DATA['jwt']['expires_in'],
            # Timestamp before accepting jwt
            "nbf": now,
            # Creation timestamp
            "iat": now,
        }
        try:
            bearer_token = jwt.encode(payload, base64.b64decode(certificate_sudo.private_key_id.pem_key), algorithm="RS256")
        except ValueError as e:
            raise UserError(_('Error on authentication. Please contact an administrator. (%s)', e))
        return bearer_token

    def _dimona_authenticate(self, declare=True):
        bearer = self._get_jwt()
        data = {
            'grant_type': 'client_credentials',
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'scope': 'scope:dimona:declaration:declarant' if declare else 'scope:dimona:declaration:consult',
            'client_assertion': bearer,
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        try:
            response = request(**API_ROUTES['authentification'], data=data, headers=headers, timeout=DIMONA_TIMEOUT)
        except HTTPError as e:
            raise UserError(_('Cannot connect with the ONSS servers. Please contact an administrator. (%s)', e))
        if response.status_code == 200:
            return self._validate_response('authentification', response)['access_token']
        if response.status_code == 400:
            raise UserError(_('Error with one or several invalid parameters on the POST request during authentication. Please contact an administrator. (%s)', response.text))
        if response.status_code == 500:
            raise UserError(_('Due to a technical problem at the ONSS side, the authentication could not be done by the ONSS.'))
        response.raise_for_status()

    def _dimona_declaration(self, data):
        self.ensure_one()
        access_token = self._dimona_authenticate()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % access_token,
        }

        try:
            response = request(**API_ROUTES['push_declaration'], json=data, headers=headers, timeout=DIMONA_TIMEOUT)
        except HTTPError as e:
            raise UserError(_('Cannot connect with the ONSS servers. Please contact an administrator. (%s)', e))

        if response.status_code == 201:
            result = response.headers
            self.l10n_be_dimona_last_declaration_number = result['Location'].split('/')[-1]
            if 'dimonaIn' in data:
                self.l10n_be_dimona_in_declaration_number = self.l10n_be_dimona_last_declaration_number
            self.l10n_be_dimona_declaration_state = 'waiting'
            self.message_post(body=_('DIMONA IN declaration posted successfully, waiting validation'))
            self.env.ref('l10n_be_hr_payroll_dimona.ir_cron_check_dimona')._trigger(fields.Datetime.now() + timedelta(minutes=1))
            return

        if response.status_code == 400:
            raise UserError(_('Error with one or several invalid parameters on the POST request. Please contact an administrator. (%s)', response.text))
        if response.status_code == 401:
            raise UserError(_('The authentication token is invalid. Please contact an administrator. (%s)', response.text))
        if response.status_code == 403:
            raise UserError(_('Your user does not have the rights to make a declaration for the employer. This happens, for example, if the user does not have or no longer has a mandate for the employer. (%s)', response.text))
        if response.status_code == 500:
            raise UserError(_('Due to a technical problem at the ONSS side, the Dimona declaration could not be received by the ONSS.'))
        response.raise_for_status()

    def _action_open_dimona(self, foreigner=False):
        self.ensure_one()

        onss_registration_number = self.company_id.onss_registration_number
        if not onss_registration_number:
            raise UserError(_('No ONSS registration number is defined for company %s', self.company_id.name))
        niss = self.employee_id.niss
        if not foreigner and not self.employee_id._is_niss_valid():
            raise UserError(_('The NISS is invalid.'))

        first_name, last_name = self.employee_id._get_split_name()
        if not first_name or not last_name:
            raise UserError(_('The employee name is incomplete'))

        if foreigner and not all(self.employee_id[field] for field in ['birthday', 'place_of_birth', 'country_of_birth', 'country_id', 'gender']):
            raise UserError(_("Foreigner employees should provide their name, birthdate, birth place, birth country, nationality and the gender"))
        if foreigner and not all(self.employee_id[f'private_{field}'] for field in ['street', 'zip', 'city', 'country_id']):
            raise UserError(_("Foreigner employees should provide a complete address (street, number, zip, city, country"))
        if not foreigner and self.employee_id.private_zip not in API_DATA['data']['municipality_by_postal_code']:
            raise UserError(_("The employee zip does not exist."))

        if self.employee_id.private_street:
            street_digits = re.findall(r"[0-9]+", self.employee_id.private_street)
            if not street_digits:
                raise UserError(_('No house number found on employee street'))
            house_number = street_digits[0]
        else:
            house_number = False

        data = {
            "employer": {
                "employerId": int(onss_registration_number),
            },
            "worker": {
                "ssin": niss if not foreigner else False,
                'lastName': last_name,
                'firstName': first_name,
                'birthDate': (self.employee_id.birthday or fields.Date.today()).strftime("%Y-%m-%d"),
                'placeOfBirth': (self.employee_id.place_of_birth or '').upper(),
                'countryOfBirth': API_DATA['data']['country_code_by_alpha2'].get(self.employee_id.country_of_birth.code),
                'nationality': API_DATA['data']['country_code_by_alpha2'].get(self.employee_id.country_id.code),
                'gender': API_DATA['data']['code_by_gender'].get(self.employee_id.gender, 'male'),
                'address': {
                    'street': self.employee_id.private_street,
                    'houseNumber': house_number,
                    'postCode': self.employee_id.private_zip,
                    'municipality': {
                        'name': self.employee_id.private_city,
                        'code': API_DATA['data']['municipality_by_city_name'].get(self.employee_id.private_city.lower())
                                or API_DATA['data']['municipality_by_postal_code'].get(self.employee_id.private_zip) or 99999,
                    },
                    'country': API_DATA['data']['country_code_by_alpha2'].get(self.employee_id.private_country_id.code)
                },
            },
            "dimonaIn": {
                "startDate": self.date_start.strftime("%Y-%m-%d"),
                "features": {
                    "jointCommissionNumber": "XXX",
                    "workerType": "OTH" if not self.l10n_be_is_student else "STU"
                }
            }
        }
        if self.date_end:
            data['dimonaIn']["endDate"] = self.date_end.strftime("%Y-%m-%d")
        if self.l10n_be_dimona_planned_hours:
            data['dimonaIn']["plannedHoursNumber"] = self.l10n_be_dimona_planned_hours
        # Drop empty worker informations (The ONSS doesn't like it)
        data['worker']['address'] = {key: value for key, value in data['worker']['address'].items() if value}
        data['worker'] = {key: value for key, value in data['worker'].items() if value}

        self._dimona_declaration(data)

    def _action_close_dimona(self):
        self.ensure_one()

        data = {
            "dimonaOut": {
                "periodId": int(self.l10n_be_dimona_in_declaration_number),
                "endDate": self.date_end.strftime("%Y-%m-%d"),
            }
        }

        self._dimona_declaration(data)

    def _action_update_dimona(self):
        self.ensure_one()

        data = {
            "dimonaUpdate": {
                "periodId": int(self.l10n_be_dimona_in_declaration_number),
                "startDate": self.date_start.strftime("%Y-%m-%d")
            }
        }
        if self.date_end:
            data["dimonaUpdate"]["endDate"] = self.date_end.strftime("%Y-%m-%d")
        if self.l10n_be_dimona_planned_hours:
            data['dimonaUpdate']["plannedHoursNumber"] = self.l10n_be_dimona_planned_hours

        self._dimona_declaration(data)

    def _action_cancel_dimona(self):
        self.ensure_one()

        data = {
            "dimonaCancel": {
                "periodId": int(self.l10n_be_dimona_in_declaration_number),
            }
        }

        self._dimona_declaration(data)

    def action_check_dimona(self):
        self.ensure_one()
        if not self.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            raise UserError(_("You don't have the right to call this action"))

        if not self.l10n_be_dimona_last_declaration_number:
            raise UserError(_("No DIMONA declaration is linked to this contract"))

        access_token = self._dimona_authenticate(declare=False)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % access_token,
        }
        try:
            response = request(
                API_ROUTES['get_declaration']['method'],
                API_ROUTES['get_declaration']['url'] + url_quote(self.l10n_be_dimona_last_declaration_number),
                headers=headers, timeout=DIMONA_TIMEOUT)
            if response.status_code == 200:
                result = response.json()
                status = result['declarationStatus']['result']
                if status == 'A':
                    self.l10n_be_dimona_declaration_state = 'done'
                    self.message_post(body=_('DIMONA declaration treated and accepted without anomalies'))
                elif status == 'W':
                    self.l10n_be_dimona_declaration_state = 'done_warning'
                    self.message_post(body=_(
                        'DIMONA declaration treated and accepted with non blocking anomalies\n%(anomalies)s\n%(informations)s',
                        anomalies=result['declarationStatus']['anomaliesCollection'],
                        informations=result['declarationStatus']['informationsCollection']))
                elif status == 'B':
                    self.l10n_be_dimona_declaration_state = 'refused'
                    self.message_post(body=_(
                        'DIMONA declaration treated and refused (blocking anomalies)\n%s',
                        result['declarationStatus']['anomaliesCollection']))
                elif status == 'S':
                    self.l10n_be_dimona_declaration_state = 'waiting_sigedis'
                    self.message_post(body=_('DIMONA declaration waiting worker identification by Sigedis'))
            elif response.status_code == 400:
                raise UserError(_('Error with one or several invalid parameters on the POST request. Please contact an administrator. (%s)', response.text))
            elif response.status_code == 403:
                raise UserError(_('Your user does not have the rights to consult this declaration. This happens, for example, if the user does not have or no longer has a mandate for the employer. (%s)', response.text))
            elif response.status_code == 404:
                raise UserError(_('The declaration has been submitted but not processed yet or the declaration reference is not known. (%s)', response.text))
            elif response.status_code == 500:
                raise UserError(_('Due to a technical problem at the ONSS side, the Dimona declaration could not be received by the ONSS.'))
            response.raise_for_status()
        except HTTPError as e:
            raise UserError(_('Cannot connect with the ONSS servers. Please contact an administrator. (%s)', e))

    @api.model
    def _cron_l10n_be_check_dimona(self, batch_size=50):
        contracts = self.search([
            ('l10n_be_dimona_declaration_state', '=', 'waiting'),
        ])
        if not contracts:
            return False
        contracts_batch = contracts[:batch_size]
        for contract in contracts_batch:
            try:
                # In case the ONSS is not available of if this is the declaration is not
                # processed yet fall silently to allow checking all the contracts of the batch
                contract.action_check_dimona()
            except Exception:
                contract.l10n_be_dimona_declaration_state = 'error'
        # if necessary, retrigger the cron to generate more pdfs
        if len(contracts) > batch_size:
            self.env.ref('l10n_be_hr_payroll_dimona.ir_cron_check_dimona')._trigger()
            return True
        return False
