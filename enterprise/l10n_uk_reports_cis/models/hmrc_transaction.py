from dateutil.relativedelta import relativedelta
from lxml import etree
from urllib.parse import urlparse

from odoo import api, fields, models
from odoo.tools.misc import format_date
from odoo.tools import float_repr, DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.l10n_uk_hmrc.models.hmrc_transaction import _send_request

class HmrcTransaction(models.Model):
    _inherit = "l10n_uk.hmrc.transaction"

    transaction_type = fields.Selection(
        string="Transaction type",
        selection_add=[('cis_monthly_return', "CIS Monthly Return")],
        ondelete={
            'cis_monthly_return': 'set default',
        },
    )
    document_attachment_id = fields.Many2one(string="Document Attachment", comodel_name='ir.attachment')

    def _generate_cis_mr_xml_data(self, credentials, document_data):
        self.ensure_one()
        nil_return_indicator = not bool(document_data['subcontractor_return_ids'])

        xml_data = {
            'credentials': credentials,
            'document': {
                'subcontractors': [],
                'contractor': {
                    'type': self.company_id.partner_id.company_type,
                    'unique_taxpayer_reference': self.company_id.l10n_uk_hmrc_unique_taxpayer_reference,
                    'account_office_reference': self.company_id.l10n_uk_hmrc_account_office_reference,
                },
                'period_end': self.period_end,
                'nil_return_indicator': nil_return_indicator,
                'employment_status': document_data['employment_status'] if not nil_return_indicator else False,
                'subcontractor_verification': document_data['subcontractor_verification'] if not nil_return_indicator else False,
                'inactivity_indicator': document_data['inactivity_indicator'],
            },
            'transaction': {
                'mode': self.env['ir.config_parameter'].sudo().get_param("l10n_uk_hmrc.api_mode", 'production'),
                'class': self._get_transaction_class(),
                'body_template': "l10n_uk_reports_cis.hmrc_cis_monthly_return_body",
            },
        }

        if not nil_return_indicator:
            for subcontractor_return_dict in document_data['subcontractor_return_ids']:
                partner = self.env['res.partner'].browse(subcontractor_return_dict['id'])
                partner.with_prefetch(document_data['subcontractor_ids'])
                xml_data['document']['subcontractors'].append({
                    'id': partner.id,
                    'type': partner.company_type,
                    'trading_name': partner.name,
                    'forename': partner.l10n_uk_reports_cis_forename,
                    'second_forename': partner.l10n_uk_reports_cis_second_forename,
                    'surname': partner.l10n_uk_reports_cis_surname,
                    'unique_taxpayer_reference': partner.l10n_uk_hmrc_unique_taxpayer_reference,
                    'company_registration_number': partner.l10n_uk_hmrc_company_registration_number,
                    'national_insurance_number': partner.l10n_uk_hmrc_national_insurance_number,
                    'cis_verification_number': partner.l10n_uk_reports_cis_verification_number,
                    'deduction_rate': partner.l10n_uk_reports_cis_deduction_rate,
                    'total_payment_made': float_repr(subcontractor_return_dict['total_payment_made'], 2),
                    'direct_cost_of_materials': float_repr(subcontractor_return_dict['direct_cost_of_materials'], 2),
                    'total_amount_deducted': float_repr(subcontractor_return_dict['total_amount_deducted'], 2),
                })
        xml_data['ir_mark'] = self._generate_ir_mark(xml_data)
        return xml_data

    def _submit_cis_mr_transaction(self, credentials, document_data):
        self.ensure_one()
        xml_data = self._generate_cis_mr_xml_data(credentials, document_data)
        monthly_return_document = self._generate_xml_document(xml_data)

        # We render it twice. The second time without credentials to store it in an attachment
        xml_data['credentials'] = {}
        monthly_return_document_safe = self._generate_xml_document(xml_data)
        document_string = etree.tostring(etree.fromstring(monthly_return_document_safe), pretty_print=True, xml_declaration=True, encoding='UTF-8').decode()
        self.document_attachment_id = self.env['ir.attachment'].create({
            'raw': document_string,
            'name': f'hmrc_transaction_document_cis_{self.period_end}.xml',
            'res_model': self._name,
            'res_id': self.id,
        })

        response, header = _send_request(self, monthly_return_document)

        if header['qualifier'] != 'acknowledgement':
            self._handle_submission_error(response, header)

        response_write_vals = {
            'next_endpoint': urlparse(header['response_end_point']).path,
            'next_polling': fields.Datetime.add(fields.Datetime.now(), seconds=int(header['poll_interval'])).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'correlation_id': header['correlation_id'],
            'state': 'polling',
        }
        self.write(response_write_vals)
        self.env.ref('l10n_uk_hmrc.ir_cron_l10n_uk_hmrc_process_transactions')._trigger()

    def _handle_success(self):
        super()._handle_success()
        email_template = self.env.ref('l10n_uk_reports_cis.email_template_cis_response_success', raise_if_not_found=False)
        if self.transaction_type == 'cis_monthly_return' and email_template:
            email_template.send_mail(
                self.id,
                force_send=True,
                email_values={'attachment_ids': self.response_attachment_id.ids},
            )

    def _handle_request_error(self, error_data, transaction_type):
        super()._handle_request_error(error_data, transaction_type)
        email_template = self.env.ref('l10n_uk_reports_cis.email_template_cis_response_failure', raise_if_not_found=False)
        if self.transaction_type == 'cis_monthly_return' and transaction_type == 'polling' and email_template:
            email_template.send_mail(
                self.id,
                force_send=True,
                email_values={'attachment_ids': self.response_attachment_id.ids},
            )

    @api.model
    def _cron_notify_cis_return(self):
        # This cron is executed every day. When it's the 6th day of the month meaning the end of the cis period,
        # we send a reminder to inform the user that he has 14 days to post it.
        today = fields.Date.today()
        if today.day != 6:
            return

        email_template = self.env.ref('l10n_uk_reports_cis.email_template_cis_notification', raise_if_not_found=False)
        if not email_template:
            return

        companies = self.env['res.company'].search([('partner_id.country_code', '=', 'GB'), ('l10n_uk_hmrc_unique_taxpayer_reference', '!=', False)])

        period_end = today + relativedelta(days=-1)  # As we are always the sixth of the month, we just need to subtract one day
        transaction_by_companies = self.env['l10n_uk.hmrc.transaction'].search([('company_id', 'in', companies.ids), ('period_end', '=', period_end)]).grouped('company_id')

        for company in companies:
            if company.id in transaction_by_companies:
                continue

            email_body = self.env['ir.qweb']._render(
                'l10n_uk_reports_cis.email_body_template_cis_notification',
                {
                    'partner_name': company.partner_id.name,
                    'period_end': format_date(self.env, period_end, company.partner_id.lang),
                    'period_due': format_date(self.env, period_end + relativedelta(days=14), company.partner_id.lang),
                },
            )
            email_body = self.env['mail.render.mixin']._replace_local_links(email_body)

            email_template.send_mail(
                company.id,
                force_send=True,
                email_values={'body_html': email_body},
            )

    def _get_transaction_class(self):
        if self.transaction_type == 'cis_monthly_return':
            return 'IR-CIS-CIS300MR'
        super()._get_transaction_class()
