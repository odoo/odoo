import requests

from dateutil.relativedelta import relativedelta
from enum import Enum
from lxml import etree
from uuid import uuid4

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import date_utils
from odoo.tools.xml_utils import find_xml_value

URN_NAMESPACE = {'urn': "urn:oio:skat:nemvirksomhed:ws:1.0.0"}
URN1_NAMESPACE = {'urn1': "urn:oio:skat:nemvirksomhed:1.0.0"}
NS_NAMESPACE = {'ns': "http://rep.oio.dk/skat.dk/TSE/angivelse/xml/schemas/2006/09/01/"}


class FrequencyCode(Enum):
    NONE_FREQUENCY_CODE = '0'
    IMMEDIATELY_FREQUENCY_CODE = '1'
    DAILY_FREQUENCY_CODE = '2'
    WEEKLY_FREQUENCY_CODE = '5'
    TWO_WEEKS_FREQUENCY_CODE = '6'
    MONTH_FREQUENCY_CODE = '7'
    QUARTER_FREQUENCY_CODE = '8'
    HALF_YEAR_FREQUENCY_CODE = '9'
    YEAR_FREQUENCY_CODE = '10'
    VARIES_FREQUENCY_CODE = '16'
    OCCASIONALLY_FREQUENCY_CODE = '17'


class L10nDkTaxReportRSUCalendarWizard(models.TransientModel):
    _name = 'l10n_dk_rsu.tax.report.calendar.wizard'
    _description = 'L10n DK Tax Report calendar service RSU'

    date_from = fields.Date(string="Period Starting Date")
    date_to = fields.Date(string="Period Ending Date")
    description = fields.Char(help="A description of the declaration type", default='Moms')
    report_id = fields.Many2one(comodel_name='account.report')
    company_id = fields.Many2one(comodel_name='res.company', readonly=True, required=True)

    def action_call_company_calendar(self):
        """
            This function will send the first request to the web service (VirksomhedKalenderHent). This will have a
            response containing the periods for which the legal entity must submit VAT Returns.
        """
        self.ensure_one()

        ReportHandler = self.env['l10n_dk.tax.report.handler']
        # Check that the information of the company and the wizard are correct before creating the body and sending it
        self._check_call_company_calendar()

        # Creation - body of the request
        body = self.env['ir.qweb']._render('l10n_dk_rsu.calendarService', {
            'transaction_id': uuid4(),
            'transaction_time': fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'company_registry': self.company_id.company_registry,
            'description': self.description,
            'date_from': self.date_from,
            'date_to': self.date_to,
        })

        envelope = ReportHandler._create_envelope(body)
        try:
            # Send the request to the endpoint
            response = requests.post(
                url="https://b2b.skat.dk/B2BVirksomhedKalenderHentWSSProxyWEB/VirksomhedKalenderHentService",
                data=envelope['data'],
                headers={'content-type': 'text/xml'},
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Sorry, something went wrong: %s", e))

        response_tree = etree.fromstring(response.text)
        # Deal with the error code
        ReportHandler._error_code_handler(response_tree)

        has_information = response_tree.xpath('.//urn:AngivelseFrekvensListe', namespaces=URN_NAMESPACE)
        if has_information is None:
            raise UserError(_("The information entered or your information's (Company registry) give an empty result"))

        response_info = {
            'start_date': find_xml_value('.//urn1:AngivelseFrekvensForholdGyldigFraDate', response_tree, namespaces=URN1_NAMESPACE),
            'frequency_code': find_xml_value('.//urn1:AngivelseFrekvensTypeCode', response_tree, namespaces=URN1_NAMESPACE),
            'deadline_date': response_tree.xpath('.//urn1:AngivelseFristKalenderFristDato', namespaces=URN1_NAMESPACE)[-1].text,
        }
        # Optional Field
        end_date = find_xml_value('.//urn1:AngivelseFrekvensForholdGyldigTilDate', response_tree, namespaces=URN1_NAMESPACE)
        if end_date is not None:
            response_info['end_date'] = end_date
        due_date = response_tree.xpath('.//urn1:AngivelseFristKalenderBetalingDato', namespaces=URN1_NAMESPACE)[-1]
        if due_date is not None:
            response_info['due_date'] = due_date
        payment_date = response_tree.xpath('.//urn1:AngivelseFristKalenderBetalingDato', namespaces=URN1_NAMESPACE)[-1]
        if payment_date is not None:
            response_info['payment_date'] = payment_date.text

        settlement_period_start, settlement_period_end = self._calculate_settlement_period(
            response_info.get('frequency_code'),
            fields.Date.to_date(response_info.get('deadline_date')),
        )

        wizard_info = self.env['l10n_dk_rsu.tax.report.submit.draft.wizard'].create({
            'frequency_code': response_info.get('frequency_code'),
            'start_date': response_info.get('start_date'),
            'deadline_date': response_info.get('deadline_date'),
            'end_date': response_info.get('end_date'),
            'due_date': response_info.get('due_date'),
            'payment_date': response_info.get('payment_date'),
            'settlement_period_start': settlement_period_start,
            'settlement_period_end': settlement_period_end,
            'report_id': self.report_id.id,
            'company_id': self.company_id.id,
        })

        return wizard_info._get_records_action(
            name=_("Tax Report RSU Submit Draft"),
            target="new",
        )

    def _check_call_company_calendar(self):
        if self.date_from == self.date_to:
            raise UserError(_("Please use a Period starting date different than your Period ending date!"))

        if not self.company_id.company_registry:
            raise RedirectWarning(
                _("No company registry associated with your company. Please define one."),
                self.env.ref('base.action_res_company_form').id,
                _("Company Settings"),
            )

    @api.model
    def _calculate_settlement_period(self, frequency_code, deadline_date):
        """
        Calculate the settlement period based on the given frequency code and deadline date.
        :param frequency_code: Code representing the frequency.
        :param deadline_date: The deadline date to calculate from.
        :return: A tuple containing the start and end dates of the settlement period.
        """
        def weekly(date):
            return date_utils.start_of(date, 'week'), date_utils.end_of(date, 'week')

        def bimonthly(date):
            start_of_week, end_of_week = weekly(date)
            return start_of_week - relativedelta(days=7), end_of_week

        def half_yearly(date):
            quarter_number = date_utils.get_quarter_number(date)
            if quarter_number % 2 == 0:
                return (
                    date_utils.start_of(date_utils.start_of(date, 'quarter') - relativedelta(days=1), 'quarter'),
                    date_utils.end_of(date, 'quarter')
                )
            return (
                date_utils.start_of(date_utils.start_of(date, 'quarter'), 'quarter'),
                date_utils.end_of(date_utils.end_of(date, 'quarter') + relativedelta(days=1), 'quarter')
            )

        match frequency_code:
            case FrequencyCode.IMMEDIATELY_FREQUENCY_CODE:
                return deadline_date, deadline_date
            case FrequencyCode.DAILY_FREQUENCY_CODE:
                return deadline_date - relativedelta(days=1), deadline_date
            case FrequencyCode.WEEKLY_FREQUENCY_CODE:
                return weekly(deadline_date)
            case FrequencyCode.TWO_WEEKS_FREQUENCY_CODE:
                return bimonthly(deadline_date)
            case FrequencyCode.MONTH_FREQUENCY_CODE:
                return date_utils.get_month(deadline_date)
            case FrequencyCode.QUARTER_FREQUENCY_CODE:
                return date_utils.get_quarter(deadline_date)
            case FrequencyCode.HALF_YEAR_FREQUENCY_CODE:
                return half_yearly(deadline_date)
            case FrequencyCode.YEAR_FREQUENCY_CODE:
                return date_utils.start_of(deadline_date, 'year'), date_utils.end_of(deadline_date, 'year')
            case _:
                return False, False


class L10nDkTaxReportRSUSubmitDraftWizard(models.TransientModel):
    _name = 'l10n_dk_rsu.tax.report.submit.draft.wizard'
    _description = 'L10n DK Tax Report Submit Draft service RSU'

    frequency_code = fields.Selection(
        selection=[
            ('0', "None"),
            ('1', "Immediately"),
            ('2', "Daily"),
            ('5', "Weekly"),
            ('6', "Every 14th day"),
            ('7', "Monthly"),
            ('8', "Quarterly"),
            ('9', "Every 6 months"),
            ('10', "Yearly"),
            ('16', "Varies"),
            ('17', "Occasionally"),
        ],
        readonly=True,
        help="How often you have to send the tax report",
    )
    start_date = fields.Date(readonly=True, help="When the company was first registered for VAT")
    deadline_date = fields.Date(readonly=True)
    end_date = fields.Date(readonly=True)
    due_date = fields.Date(readonly=True)
    payment_date = fields.Date(readonly=True)
    settlement_period_start = fields.Date()
    settlement_period_end = fields.Date()
    report_id = fields.Many2one(comodel_name='account.report')
    company_id = fields.Many2one(comodel_name='res.company', readonly=True)

    def action_submit_draft(self):
        self.ensure_one()

        lines = self.report_id._get_lines(self.report_id.get_options())
        ReportHandler = self.env['l10n_dk.tax.report.handler']

        def get_line_value_from_xmlid(lines, xmlid):
            return self.env.company.currency_id.round(self.env['account.report']._get_line_from_xml_id(lines, xmlid)['columns'][0]['no_format'])

        body = self.env['ir.qweb']._render('l10n_dk_rsu.submitDraftService', {
            'transaction_id': uuid4(),
            'transaction_time': fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'company_registry': self.company_id.company_registry,
            'settlement_start': self.settlement_period_start,
            'settlement_end': self.settlement_period_end,
            'vat_declaration': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_vat_statement'),
            'co2_tax': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_deduction_co2_tax'),
            'categoryA_goods': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_section_a_products'),
            'categoryB_eu_goods': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_section_b_product_eu'),
            'categoryB_non_eu_goods': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_section_b_products_non_eu'),
            'electricity': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_deduction_electrical_tax'),
            'categoryC_other_goods_service': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_section_c'),
            'natural_or_town_gas': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_deduction_gas_tax'),
            'purchase_vat': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_deduction_purchase_tax'),
            'coal': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_deduction_coal_tax'),
            'vat_on_purchase_goods': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_international_purchase_products'),
            'vat_on_purchase_services': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_international_purchase_services'),
            'oil': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_deduction_oil_bottle_tax'),
            'sale_vat': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_sales_tax'),
            'water': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_deduction_water_tax'),
            'categoryA_benefits': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_section_a_services'),
            'categoryB_services': get_line_value_from_xmlid(lines, 'l10n_dk.account_tax_report_line_section_b_services'),
        })

        envelope = ReportHandler._create_envelope(body)
        try:
            # Send the request to the endpoint
            response = requests.post(
                url="https://b2b.skat.dk/B2BModtagMomsangivelseForeloebigWSSProxyWEB/ModtagMomsangivelseForeloebigService",
                data=envelope['data'],
                headers={'content-type': 'text/xml'},
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Sorry, something went wrong: %s", e))

        response_tree = etree.fromstring(response.text)
        # Deal with the error code
        ReportHandler._error_code_handler(response_tree)

        transaction_identifier = response_tree.xpath('.//urn1:TransaktionIdentifier', namespaces=URN1_NAMESPACE)
        if transaction_identifier is None:
            raise UserError(_("The information entered give an empty result"))

        wizard_info = self.env['l10n_dk_rsu.tax.report.receipt.wizard'].create({
            'transaction_identifier': transaction_identifier[-1].text,
            'link': find_xml_value('.//urn1:UrlIndicator', response_tree, namespaces=URN1_NAMESPACE),
            'company_id': self.company_id.id,
        })

        return wizard_info._get_records_action(
            name=_("Tax Report RSU Receipt"),
            target="new",
        )


class L10nDkTaxReportRSUReceiptWizard(models.TransientModel):
    _name = 'l10n_dk_rsu.tax.report.receipt.wizard'
    _description = 'L10n DK Tax Report receipt service RSU'

    link = fields.Char()
    transaction_identifier = fields.Char()
    is_report_approved = fields.Boolean()
    is_receipt_received = fields.Boolean()

    ocr_card_type_code = fields.Char(readonly=True)
    ocr_identification_number = fields.Char(readonly=True)
    ocr_account_number = fields.Char(readonly=True)
    payment_ref = fields.Char(readonly=True)
    deadline_date = fields.Date(readonly=True)
    attachment = fields.Binary(attachment=True)
    company_id = fields.Many2one(comodel_name='res.company', readonly=True)

    def action_receive_receipt(self):
        self.ensure_one()

        ReportHandler = self.env['l10n_dk.tax.report.handler']
        body = self.env['ir.qweb']._render('l10n_dk_rsu.receiptService', {
            'transaction_id': uuid4(),
            'transaction_time': fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'received_transaction_identifier': self.transaction_identifier,
            'company_registry': self.company_id.company_registry,
        })

        envelope = ReportHandler._create_envelope(body)
        try:
            # Send the request to the endpoint
            response = requests.post(
                url="https://b2b.skat.dk/B2BMomsangivelseKvitteringHentWSSProxyWEB/MomsangivelseKvitteringHentService",
                data=envelope['data'],
                headers={'content-type': 'text/xml'},
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Sorry, something went wrong: %s", e))

        response_tree = etree.fromstring(response.text)
        # Deal with the error code
        ReportHandler._error_code_handler(response_tree)

        encoded_pdf = response_tree.xpath('.//urn1:DokumentFilIndholdData', namespaces=URN1_NAMESPACE)
        if encoded_pdf is None:
            raise UserError(_("The receipt has not been received."))

        self.is_receipt_received = True
        self.attachment = encoded_pdf[-1].text
        self.ocr_card_type_code = find_xml_value('.//urn1:OCRKortTypeKode', response_tree, namespaces=URN1_NAMESPACE)
        self.ocr_identification_number = find_xml_value('.//ns:OCRnummerIdentifikator', response_tree, namespaces=NS_NAMESPACE)
        self.ocr_account_number = find_xml_value('.//urn1:OCRKontoNummerIdentifikator', response_tree, namespaces=URN1_NAMESPACE)
        self.payment_ref = find_xml_value('.//urn1:BetalingIkkeBetaltBeloeb', response_tree, namespaces=URN1_NAMESPACE)
        self.deadline_date = find_xml_value('.//urn1:AngivelseFristKalenderBetalingDato', response_tree, namespaces=URN1_NAMESPACE)

        return self._get_records_action(
            name=_("Tax Report RSU Receipt"),
            target="new",
        )

    def action_approve_tax_report(self):
        self.ensure_one()

        self.is_report_approved = True
        return {
            "name": "Approve tax report",
            "type": "ir.actions.act_url",
            "url": self.link,
        }

    def action_download_pdf(self):
        self.ensure_one()

        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('res_field', '=', 'attachment'),  # The binary field name
        ], limit=1)

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}",
            "target": "new",
        }
