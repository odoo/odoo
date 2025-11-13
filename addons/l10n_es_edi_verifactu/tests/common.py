import base64
import json
import requests

from unittest import mock

from odoo import _, release, Command
from odoo.tools import file_open, html_sanitize, misc, zeep
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestL10nEsEdiVerifactuCommon(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()

        fake_db_identifier = '7244834601315494189'
        db_identifier_function = 'odoo.addons.l10n_es_edi_verifactu.models.verifactu_document.L10nEsEdiVerifactuDocument._get_db_identifier'
        patch_db_identifier = mock.patch(db_identifier_function, lambda _self: fake_db_identifier)
        cls.startClassPatcher(patch_db_identifier)

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        cls.other_currency = cls.setup_other_currency('USD')

        certificate_path = 'l10n_es_edi_verifactu/demo/certificates/Certificado_RPJ_A39200019_CERTIFICADO_ENTIDAD_PRUEBAS_5_Pre.p12'
        cls.certificate = cls.env['certificate.certificate'].create({
            'content': base64.encodebytes(misc.file_open(certificate_path, 'rb').read()),
            'pkcs12_password': '1234',
            'scope': 'verifactu',
        })

        cls.company = cls.company_data['company']
        cls.company.write({
            'country_id': cls.env.ref('base.es').id,
            'state_id': cls.env.ref('base.state_es_z').id,
            # Use the VAT / NIF that was used to generate the responses
            # This is needed to have the correct record identifiers on the invoices
            'vat': 'ESA39200019',
            'l10n_es_edi_verifactu_required': True,
            'l10n_es_edi_verifactu_certificate_ids': [Command.set(cls.certificate.ids)],
            'l10n_es_edi_verifactu_test_environment': True,
        })
        # Create a second Spanish Company. To ensure we set `IndicadorMultiplesOT` correctly
        cls.company_data_2 = cls.setup_other_company(country_id=cls.env.ref('base.es').id)

        cls.partner_a.write({
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.partner_b.write({
            'vat': 'ESF35999705',
        })

        cls.product_1 = cls.env['product.product'].create({
           'name': "Product 1",
        })

        ChartTemplate = cls.env['account.chart.template'].with_company(cls.company)
        cls.tax21_goods = ChartTemplate.ref('account_tax_template_s_iva21b')
        cls.tax21_services = ChartTemplate.ref('account_tax_template_s_iva21s')
        cls.tax10_goods = ChartTemplate.ref('account_tax_template_s_iva10b')
        cls.tax10_services = ChartTemplate.ref('account_tax_template_s_iva10s')
        cls.tax1p4_services_recargo = ChartTemplate.ref('account_tax_template_s_req014')
        cls.tax5p2_services_recargo = ChartTemplate.ref('account_tax_template_s_req52')
        cls.tax1_withholding = ChartTemplate.ref('account_tax_template_s_irpf1')
        cls.tax0_no_sujeto_loc = ChartTemplate.ref('account_tax_template_s_iva_ns')
        cls.tax0_isp = ChartTemplate.ref('account_tax_template_s_iva0_isp')
        cls.tax0_exento = ChartTemplate.ref('account_tax_template_s_iva0')
        cls.tax0_exento_export = ChartTemplate.ref('account_tax_template_s_iva0_g_e')
        # We create a 'no_sujeto' tax since there is currently no such tax in the standard chart
        cls.tax0_no_sujeto = cls.tax0_no_sujeto_loc.copy()
        cls.tax0_no_sujeto.l10n_es_type = 'no_sujeto'

        # Everything in the tests should be possible without being administrator.
        # We do not want to hide access errors the user may have in production (i.e. with access to the certificates)
        cls.user.group_ids = [Command.unlink(cls.env.ref('base.group_system').id)]

        # Do not do any zeep operations by default.
        # I.e. do not do xml / xsd validation during tests (needs network connection to create the client).
        cls.startClassPatcher(cls._mock_get_zeep_operation(None, None, None))

        # Do avoid updating the test files for every version we just assume that we are in 17.0
        cls.startClassPatcher(mock.patch.object(release, 'version', '17.0+e'))

    @classmethod
    def _read_file(cls, path, *args):
        with file_open(path, *args) as f:
            content = f.read()
        return content

    def _json_file_to_dict(self, json_file):
        json_string = self._read_file(json_file, 'rb')
        return json.loads(json_string)

    def _mock_response(self, status_code, response_file, content_type='text/xml;charset=UTF-8'):
        response = mock.Mock(spec=requests.Response)
        response.status_code = status_code
        response.text = self._read_file(response_file)
        response.content = response.text.encode()
        response.headers = {
            'content-type': content_type,
        }
        return response

    def _mock_request(self, mock_response):
        request_function_path = 'odoo.addons.l10n_es_edi_verifactu.models.verifactu_document.L10nEsEdiVerifactuDocument._soap_request'
        return mock.patch(request_function_path, return_value=mock_response)

    def _mock_get_zeep_operation(self, registration_return_value=None, registration_xml_return_value=None):
        request_function_path = 'odoo.addons.l10n_es_edi_verifactu.models.verifactu_document._get_zeep_operation'

        def mocked_get_zeep_operation(company, operation):
            if operation not in ('registration', 'registration_xml'):
                raise NotImplementedError()
            function = registration_return_value if operation == 'registration' else registration_xml_return_value
            return (function, {})

        return mock.patch(request_function_path, mocked_get_zeep_operation)

    def _mock_zeep_registration_operation(self, response_file_json):
        # Note: The real result is of type 'odoo.tools.zeep.client.SerialProxy'; here it is a dict
        zeep_response_dict = json.loads(self._read_file(response_file_json))
        return self._mock_get_zeep_operation(registration_return_value=lambda *args, **kwargs: zeep_response_dict)

    def _mock_zeep_registration_operation_certificate_issue(self):
        def _raise_certificate_error(*args, **kwargs):
            certificate_error = "No autorizado. Se ha producido un error al verificar el certificado presentado"
            raise zeep.exceptions.TransportError(certificate_error)

        return self._mock_get_zeep_operation(registration_return_value=_raise_certificate_error)

    def _mock_cron_trigger(self, cron_trigger_result_dict):
        trigger_function_path = 'odoo.addons.base.models.ir_cron.IrCron._trigger'

        def _put_at_in_dict(self, at=None):
            cron_trigger_result_dict['at'] = at

        return mock.patch(trigger_function_path, _put_at_in_dict)

    def _mock_format_document_errors(self, errors, title):
        """Mock the computation of field `errors` of model 'l10n_es_edi_verifactu.document' from a list of translated errors."""
        error = {
            'error_title': title,
            'errors': errors,
        }
        return html_sanitize(self.env['account.move.send']._format_error_html(error))

    def _mock_format_document_generic_errors(self, errors):
        title = _("Error")
        return self._mock_format_document_errors(errors, title)

    def _mock_format_document_aeat_errors(self, errors):
        title = _("The Veri*Factu document contains the following errors according to the AEAT")
        return self._mock_format_document_errors(errors, title)

    def _mock_format_document_generation_errors(self, errors):
        title = _("The Veri*Factu document could not be created")
        return self._mock_format_document_errors(errors, title)

    def _mock_last_document(self, document):
        # Note: returns the same document for all companies
        function_path = 'odoo.addons.l10n_es_edi_verifactu.models.res_company.ResCompany._l10n_es_edi_verifactu_get_last_document'
        return mock.patch(function_path, return_value=(document or self.env['l10n_es_edi_verifactu.document']))

    def _mock_create_date(self, date):
        return mock.patch.object(self.env.cr, 'now', lambda: date)

    def _create_dummy_invoice(self, name=None, invoice_date=None):
        # The only values we care about are the ones relevant for the record identifier.
        invoice_vals = {
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-30',
            'date': '2019-01-30',
            'partner_id': self.partner_b.id,  # Spanish customer
            'invoice_line_ids': [
                Command.create({'product_id': self.product_1.id, 'price_unit': 100.0, 'tax_ids': [Command.set(self.tax21_goods.ids)]}),
            ],
        }

        # Adjust some values to give the record the needed record identifier
        if invoice_date is not None:
            invoice_vals['invoice_date'] = invoice_date
        if name is not None:
            invoice_vals['name'] = name

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()

        return invoice
