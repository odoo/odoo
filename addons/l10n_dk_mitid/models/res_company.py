import logging
import threading

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)

# TODO: To be replaced with IAP url once it's ready (ask for DNS)
# TODO: probably https://nemhandel.api.odoo.com or https://mitid.api.odoo.com
IAP_ENDPOINT = 'https://hot-wombat-patient.ngrok-free.app'
COMPANY_INFO_TIMEOUT = 5
# The company data written on the electronic documents, that must match the CVR register
CVR_LOCKED_FIELDS = ['name', 'vat', 'street', 'street2', 'zip', 'city', 'country_id']


class ResCompany(models.Model):
    _inherit = 'res.company'

    mitid_kyc_status = fields.Selection(
        selection=[
            ('processing', "Processing"),
            ('success', "Success"),
            ('fail', "Fail"),
        ],
    )
    mitid_authentication_uuid = fields.Char(
        string="Authentication IAP UUID",
        groups='account.group_account_invoice',
    )

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        if not getattr(threading.current_thread(), 'testing', False):
            companies._mitid_autofill_from_cvr()
        return companies

    def _mitid_get_iap_url(self):
        return IAP_ENDPOINT

    def _mitid_prepare_values_from_company_info(self, company_info):
        self.ensure_one()
        address = company_info.get('address') or {}
        country = address.get('country_code') and self.env['res.country'].search([('code', '=', address['country_code'])], limit=1)
        return {
            'name': company_info.get('name'),
            'vat': company_info.get('cvr') and f"DK{company_info['cvr']}",
            'street': address.get('street'),
            'street2': address.get('street2'),
            'zip': address.get('zip'),
            'city': address.get('city'),
            'country_id': country.id if country else False,
            'email': company_info.get('email'),
            'phone': company_info.get('phone'),
        }

    def _mitid_get_company_info(self):
        """ Gets the data of the company from the CVR register, through IAP.

        :return: the company data, or a dict with an 'error' and its 'code' if the IAP route failed
        """
        self.ensure_one()
        return iap_tools.iap_jsonrpc(
            f'{self._mitid_get_iap_url()}/api/mitid_id_authentication/1/company_info',
            params={'cvr': self.company_registry},
            timeout=COMPANY_INFO_TIMEOUT,
        )

    def _mitid_write_cvr_values(self, values):
        self.ensure_one()
        values = dict(values)
        vat = values.pop('vat', None)
        self.write(values)
        if vat:
            try:
                with self.env.cr.savepoint():
                    self.vat = vat
            except ValidationError:
                # e.g. the test CVR numbers are not valid VAT numbers
                _logger.info("The CVR number of the company %s is not a valid VAT number", self.id)

    def _mitid_get_company_differences(self, company_info):
        """ Compares the company data with the CVR register.

        :return: a list of dicts with the 'field', its 'label', the 'current_value' and 'cvr_value' to display,
                 and the 'value' to write to match the CVR register
        """
        self.ensure_one()

        def normalize(value):
            return ' '.join(str(value or '').split()).casefold()

        cvr_values = self._mitid_prepare_values_from_company_info(company_info)
        if cvr_values['vat'] and not self.env['res.partner'].simple_vat_check('dk', company_info['cvr']):
            # The company couldn't be updated with an invalid VAT number
            cvr_values['vat'] = False
        differences = []
        for field_name in CVR_LOCKED_FIELDS:
            cvr_value = cvr_values.get(field_name)
            # A value missing from the CVR register is not a difference, e.g. the CVR has no second address line
            if not cvr_value:
                continue
            if field_name == 'country_id':
                country = self.env['res.country'].browse(cvr_value)
                if self.country_id == country:
                    continue
                current_display, cvr_display = self.country_id.name, country.name
            else:
                if field_name == 'vat':
                    is_same = normalize(self.vat).replace(' ', '') == normalize(cvr_value)
                else:
                    is_same = normalize(self[field_name]) == normalize(cvr_value)
                if is_same:
                    continue
                current_display, cvr_display = self[field_name], cvr_value
            differences.append({
                'field': field_name,
                'label': self._fields[field_name]._description_string(self.env),
                'current_value': current_display or '',
                'cvr_value': cvr_display,
                'value': cvr_value,
            })
        return differences

    def _mitid_autofill_from_cvr(self):
        """ Fills the empty fields of the Danish companies with the data of the CVR register. """
        for company in self:
            if not company.company_registry or (company.country_id and company.country_code != 'DK'):
                continue
            try:
                company_info = company._mitid_get_company_info()
            except Exception:  # noqa: BLE001
                # The company must be created even if the CVR register can't be reached
                _logger.warning("Could not get the CVR information of the company %s", company.id, exc_info=True)
                continue
            if company_info.get('error'):
                _logger.info("No CVR information for the company %s: %s", company.id, company_info['error'])
                continue
            values = company._mitid_prepare_values_from_company_info(company_info)
            # Never override what the user has filled in
            values = {field: value for field, value in values.items() if value and not company[field]}
            company._mitid_write_cvr_values(values)

    def _refresh_mitid_authentication_status(self, send_bus=True):
        self.ensure_one()
        response = iap_tools.iap_jsonrpc(f'{self._mitid_get_iap_url()}/api/mitid_id_authentication/1/kyc_status', params={
            'object_uuid': self.mitid_authentication_uuid,
        })
        if response.get('kyb_status') == 'success' and response.get('kyc_status') == 'success':
            self.mitid_kyc_status = 'success'
            if self.env['account.move']._can_commit():
                self.env.cr.commit()
            if not send_bus:  # If called manually from the wizard we do not need the JS to handle it
                return
            nemhandel_registration = self.env['nemhandel.registration'].search([
                ('mitid_authentication_uuid', '=', self.mitid_authentication_uuid),
            ], order='id DESC', limit=1)
            if user := nemhandel_registration.create_uid:
                user._bus_send(
                    'mitid_auth_done',
                    {'nemhandel_registration_id': nemhandel_registration.id},
                )
