import base64
import datetime
import json
import requests

from freezegun import freeze_time
from unittest import mock

from odoo import _, Command
from odoo.tools import file_open, html_sanitize, misc, zeep
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestL10nEsEdiVerifactuCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='es_full'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.fakenow = datetime.datetime(2024, 12, 5)
        cls.startClassPatcher(freeze_time(cls.fakenow))

        fake_db_identifier = '7244834601315494189'
        db_identifier_function = 'odoo.addons.l10n_es_edi_verifactu.models.verifactu_document.L10nEsEdiVerifactuDocument._get_db_identifier'
        patch_db_identifier = mock.patch(db_identifier_function, lambda _self: fake_db_identifier)
        cls.startClassPatcher(patch_db_identifier)

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        certificate_path = 'l10n_es_edi_verifactu/demo/certificates/Certificado_RPJ_A39200019_CERTIFICADO_ENTIDAD_PRUEBAS_4_Pre.p12'
        cls.certificate = cls.env['l10n_es_edi_verifactu.certificate'].create({
            'content': base64.encodebytes(misc.file_open(certificate_path, 'rb').read()),
            'password': '1234',
        })

        cls.company = cls.company_data['company']
        cls.company.write({
            'country_id': cls.env.ref('base.es').id,
            'state_id': cls.env.ref('base.state_es_z').id,
            'vat': 'ES59962470K',
            'l10n_es_edi_verifactu_required': True,
            'l10n_es_edi_verifactu_certificate_ids': [Command.set(cls.certificate.ids)],
            'l10n_es_edi_verifactu_test_environment': True,
        })

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

        cls.tax21_goods = cls.env['account.chart.template'].with_company(cls.company).ref('account_tax_template_s_iva21b')
        cls.tax21_services = cls.env['account.chart.template'].with_company(cls.company).ref('account_tax_template_s_iva21s')
        cls.tax10_goods = cls.env['account.chart.template'].with_company(cls.company).ref('account_tax_template_s_iva10b')
        cls.tax10_services = cls.env['account.chart.template'].with_company(cls.company).ref('account_tax_template_s_iva10s')
        cls.tax1p4_services_recargo = cls.env['account.chart.template'].with_company(cls.company).ref('account_tax_template_s_req014')
        cls.tax5p2_services_recargo = cls.env['account.chart.template'].with_company(cls.company).ref('account_tax_template_s_req52')
        cls.tax1_withholding = cls.env['account.chart.template'].with_company(cls.company).ref('account_tax_template_s_irpf1')

        # Everything in the tests should be possible without being administrator.
        # We do not want to hide access errors the user may have in production (i.e. with access to the certificates)
        cls.user.groups_id = [Command.unlink(cls.env.ref('base.group_system').id)]

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

    def _mock_zeep_registration_operation_function(self, register_function):
        request_function_path = 'odoo.addons.l10n_es_edi_verifactu.models.verifactu_document.L10nEsEdiVerifactuDocument._get_zeep_registration_operations'
        return mock.patch(request_function_path, return_value=register_function)

    def _mock_zeep_registration_operation(self, response_file_json):
        # Note: The real result is of type 'odoo.tools.zeep.client.SerialProxy'; here it is a dict
        zeep_response_dict = json.loads(self._read_file(response_file_json))
        return self._mock_zeep_registration_operation_function(lambda *args, **kwargs: zeep_response_dict)

    def _mock_zeep_registration_operation_certificate_issue(self):
        def _raise_certificate_error(*args, **kwargs):
            certificate_error = "No autorizado. Se ha producido un error al verificar el certificado presentado"
            raise zeep.exceptions.TransportError(certificate_error)

        return self._mock_zeep_registration_operation_function(_raise_certificate_error)

    def _mock_cron_trigger(self, cron_trigger_result_dict):
        trigger_function_path = 'odoo.addons.base.models.ir_cron.ir_cron._trigger'

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
