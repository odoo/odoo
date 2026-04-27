# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.tools.misc import file_path
from odoo.exceptions import ValidationError
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc

import base64
from datetime import datetime
import re

uid_bfs_pattern = r'CHE-[0-9]{3}\.[0-9]{3}\.[0-9]{3}'
IAP_SERVICE_NAME = 'l10n_ch_swissdec_proxy'
DEFAULT_IAP_ENDPOINT = 'https://l10n-ch-swissdec.api.odoo.com'

def validate_second_operand(operand):
    pattern = r'[-]?[0-9]+\.[0-9]{2}'
    match = re.fullmatch(pattern, operand)
    if not match:
        raise ValidationError(_("Second Operand does not match the right pattern"))


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ch_avs_institution_ids = fields.One2many("l10n.ch.social.insurance", "company_id")
    l10n_ch_caf_institution_ids = fields.One2many("l10n.ch.compensation.fund", "company_id")
    l10n_ch_laa_institution_ids = fields.One2many("l10n.ch.accident.insurance", "company_id")
    l10n_ch_laac_institution_ids = fields.One2many("l10n.ch.additional.accident.insurance", "company_id")
    l10n_ch_ijm_institution_ids = fields.One2many("l10n.ch.sickness.insurance", "company_id")
    l10n_ch_lpp_institution_ids = fields.One2many("l10n.ch.lpp.insurance", "company_id")
    l10n_ch_work_location_ids = fields.One2many("l10n.ch.location.unit", "company_id")
    l10n_ch_st_institution_ids = fields.One2many("l10n.ch.source.tax.institution", "company_id")
    l10n_ch_salary_certificate_profiles = fields.One2many("l10n.ch.salary.certificate.profile", "company_id")

    # Delegate Information
    l10n_ch_additional_line = fields.Char("Additional Line")
    l10n_ch_uses_delegate = fields.Boolean(help="Enable this option if you delegate payroll accounting tasks to an external provider", string="Delegate Payroll Accounting")
    l10n_ch_swissdec_delegate_name = fields.Char(string="Delegate Name")
    l10n_ch_swissdec_delegate_ch_uid = fields.Char(string="Delegate Identification Number (IDE-OFS)")
    l10n_ch_delegate_Po_Box = fields.Char(string="Delegate PO. Box")
    l10n_ch_delegate_street = fields.Char()
    l10n_ch_delegate_street2 = fields.Char()
    l10n_ch_delegate_zip = fields.Char()
    l10n_ch_delegate_city = fields.Char()
    l10n_ch_delegate_state_id = fields.Many2one('res.country.state', domain="[('country_id', '=?', l10n_ch_delegate_country_id)]")
    l10n_ch_delegate_country_id = fields.Many2one('res.country', default=lambda self: self.env.ref('base.ch').id)

    l10n_ch_agricole_company = fields.Boolean(string="Agricultural Company")

    l10n_ch_statistics_convention = fields.Selection(string="Statistics Pay Agreement",
                                                     selection=[("CLA-Association", "Collective agreement of an association"),
                                                                ("CLA-BusinessOrGovernment", "Collective labor agreement of a company or a public administration"),
                                                                ("collectiveContractOutside-CLA", "Wage agreement outside of a collective agreement"),
                                                                ("individualContract", "Individual employment contract")], default="individualContract")
    l10n_ch_statistics_payroll_unit = fields.Char(string="Statistics Payroll Unit")
    l10n_ch_contact_person_name = fields.Char()
    l10n_ch_contact_person_email = fields.Char()
    l10n_ch_contact_person_phone = fields.Char()

    l10n_ch_30_day_method = fields.Boolean(string="30-Day Calculation Method", help="Compute Salaries based on the 30 day method")

    l10n_ch_transmission_language = fields.Selection(selection=[('de', 'DE - German'),
                                                                ('fr', 'FR - French'),
                                                                ('it', 'IT - Italian')], default='fr')

    @api.constrains('l10n_ch_swissdec_delegate_ch_uid')
    def _check_l10n_ch_swissdec_delegate_ch_uid(self):
        for company in self:
            if company.l10n_ch_swissdec_delegate_ch_uid:
                if re.fullmatch(uid_bfs_pattern, company.l10n_ch_swissdec_delegate_ch_uid):
                    if not self._l10n_ch_modulo_11_checksum(company.l10n_ch_swissdec_delegate_ch_uid, 8):
                        raise ValidationError(_("Delegate Identification Number (IDE-OFS) checksum is not correct"))
                else:
                    raise ValidationError(_("Delegate Identification Number (IDE-OFS) does not match the right format"))

    def _l10n_ch_swissdec_request(self, route, **kwargs):
        self.ensure_one()
        company_name = self.name

        default_endpoint = DEFAULT_IAP_ENDPOINT
        url = f'{default_endpoint}/api/l10n_ch_swissdec/1/{route}'

        params = {
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            **kwargs
        }
        report_language = self.l10n_ch_transmission_language if self.l10n_ch_transmission_language else 'de'

        if route in ['declare_salary',
                     'get_status_from_declare_salary',
                     'get_result_from_declare_salary',
                     'get_dialog',
                     'reply_dialog',
                     'create_eiv_file',
                     'generate_tax_accounting_report',
                     'generate_source_tax_report',
                     'generate_report']:
            params['company_name'] = company_name
            params["language"] = report_language

        is_neutralized = self.env['ir.config_parameter'].sudo().get_param('database.is_neutralized')
        if route in ['declare_salary',
                     'get_status_from_declare_salary',
                     'get_result_from_declare_salary',
                     'get_dialog',
                     'reply_dialog',
                     'create_eiv_file'] and is_neutralized:
            raise ValidationError(_("This feature is only allowed in production environments."))

        if route in ['generate_tax_accounting_report']:
            params['from_person'] = kwargs.get('from_person', 1)
            params['to_person'] = kwargs.get('to_person', 1)
            if 'split_files' in kwargs:
                params['split_files'] = kwargs.get('split_files')

        response = iap_jsonrpc(url, params=params, timeout=120)
        result = response.get('result')

        if result and result.get('result') == 'success':
            return result.get('data')

        message = result.get('message') if result else None
        if message:
            raise ValidationError(message)

        error = response.get('error') if response else None
        if error == 'not_enterprise':
            raise ValidationError(_("This feature is only allowed in production environments."))

    def l10n_ch_hr_payroll_action_ping(self):
        result = self._l10n_ch_swissdec_request('ping')
        return result

    def l10n_ch_hr_payroll_action_check_interoperability(self, second_operand):
        validate_second_operand(second_operand)
        result = self._l10n_ch_swissdec_request('check_interoperability',  second_operand=second_operand)
        return result
