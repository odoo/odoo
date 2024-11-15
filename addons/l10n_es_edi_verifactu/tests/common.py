import base64
import datetime
import requests
from freezegun import freeze_time
from unittest import mock

from odoo import _, Command
from odoo.tools import file_open, html_sanitize, misc
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestL10nEsEdiVerifactuCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='es_full'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.fakenow = datetime.datetime(2024, 12, 5)
        cls.startClassPatcher(freeze_time(cls.fakenow))

        fake_db_identifier = '7244834601315494189'
        db_identifier_function = 'odoo.addons.l10n_es_edi_verifactu.models.verifactu_xml.L10nEsEdiVerifactuXml._get_db_identifier'
        patch_db_identifier = mock.patch(db_identifier_function, lambda _self: fake_db_identifier)
        cls.startClassPatcher(patch_db_identifier)

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        certificate_path = "l10n_es_edi_verifactu/demo/certificates/Certificado_RPJ_A39200019_CERTIFICADO_ENTIDAD_PRUEBAS_4_Pre.p12"
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

        cls.tax21_goods = cls.env["account.chart.template"].with_company(cls.company).ref("account_tax_template_s_iva21b")
        cls.tax21_services = cls.env["account.chart.template"].with_company(cls.company).ref("account_tax_template_s_iva21s")
        cls.tax10_goods = cls.env["account.chart.template"].with_company(cls.company).ref("account_tax_template_s_iva10b")
        cls.tax10_services = cls.env["account.chart.template"].with_company(cls.company).ref("account_tax_template_s_iva10s")
        cls.tax_s_req014 = cls.env["account.chart.template"].with_company(cls.company).ref("account_tax_template_s_req014")
        cls.tax_s_req52 = cls.env["account.chart.template"].with_company(cls.company).ref("account_tax_template_s_req52")

    @classmethod
    def _read_file(cls, path, *args):
        with file_open(path, *args) as f:
            content = f.read()
        return content

    def _assert_verifactu_xml(self, xml, file):
        expected_xml = self._read_file(file, 'rb')
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(xml),
            self.get_xml_tree_from_string(expected_xml),
        )

    def _mock_response(self, status_code, response_file, content_type='text/xml;charset=UTF-8'):
        response = mock.Mock(spec=requests.Response)
        response.status_code = status_code
        response.text = self._read_file(response_file)
        response.headers = {
            'content-type': content_type,
        }
        return response

    def _mock_request(self, mock_response):
        _request_function = 'odoo.addons.l10n_es_edi_verifactu.models.verifactu_document.L10nEsEdiVerifactuDocument._request'
        return mock.patch(_request_function, return_value=mock_response)

    def _mock_format_record_document_errors(self, errors, title):
        """Mock the computation of field `errors` of model 'l10n_es_edi_verifactu.record_document' from a list of errors.
        1. Same content
        2. Mock the sanitizing performed when writing the content to an 'Html' field
        """
        error = {
            'error_title': title,
            'errors': errors,
        }
        return html_sanitize(self.env['account.move.send']._format_error_html(error))

    def _mock_format_record_document_response_parsing_errors(self, errors):
        title = _("There was an issue parsing the reponse from the AEAT")
        return self._mock_format_record_document_errors(errors, title)

    def _mock_format_record_document_response_record_errors(self, errors):
        title = _("The Veri*Factu record contains the following errors according to the AEAT")
        return self._mock_format_record_document_errors(errors, title)

    def _mock_format_record_document_response_document_errors(self, errors):
        title = _("There was an issue sending the batch document to the AEAT")
        return self._mock_format_record_document_errors(errors, title)

    def _mock_format_record_document_generation_errors(self, errors):
        title = _("The Veri*Factu record could not be created")
        return self._mock_format_record_document_errors(errors, title)
