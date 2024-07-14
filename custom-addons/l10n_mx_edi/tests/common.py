# coding: utf-8
from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tools import misc
from odoo.tools.zeep.client import SERIALIZABLE_TYPES

import base64
import logging
import pprint

from contextlib import contextmanager
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from freezegun.api import FakeDatetime
from lxml import etree
from unittest.mock import patch
from unittest import SkipTest

_logger = logging.getLogger(__name__)

# Allow the whole test suite to work as 'external' tests and really send the documents to the PAC
# in order to ensure their validity.
# [!] DON'T COMMIT THE CHANGE OF THIS VALUE
EXTERNAL_MODE = False

# For external trade, we need to use the rate of the day. The first time you send a document, you will get
# a message from the government with the rate of the day. Put it here to validate your documents.
# [!] DON'T COMMIT THE CHANGE OF THIS VALUE
RATE_WITH_USD = 17.1098

# The rate with the USD used by tests in _extended.
# RATE_WITH_USD will be used when EXTERNAL_MODE is true, TEST_RATE_WITH_USD otherwise.
TEST_RATE_WITH_USD = 16.9995


class TestMxEdiCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='mx'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.frozen_today = fields.datetime.now()

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        # ==== Config ====

        with freeze_time(cls.frozen_today):
            cls.certificate = cls.env['l10n_mx_edi.certificate'].create({
                'content': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.cer', 'rb').read()),
                'key': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.key', 'rb').read()),
                'password': '12345678a',
            })
        cls.certificate.write({
            'date_start': '2016-01-01',
            'date_end': '2018-01-01',
        })

        # do not use demo data and avoid having duplicated companies
        cls.env['res.company'].search([('vat', '=', "EKU9003173C9")]).write({'vat': False})
        cls.env['res.company'].search([('name', '=', "ESCUELA KEMPER URGATE")]).name += " (2)"

        cls.company_data['company'].write({
            'name': "ESCUELA KEMPER URGATE",
            'vat': 'EKU9003173C9',
            'street': 'Campobasso Norte 3206 - 9000',
            'street2': 'Fraccionamiento Montecarlo',
            'zip': '20914',
            'city': 'Jesús María',
            'country_id': cls.env.ref('base.mx').id,
            'state_id': cls.env.ref('base.state_mx_ags').id,
            'l10n_mx_edi_pac': 'solfact',
            'l10n_mx_edi_pac_test_env': True,
            'l10n_mx_edi_fiscal_regime': '601',
            'l10n_mx_edi_certificate_ids': [Command.set(cls.certificate.ids)],
        })

        with freeze_time(cls.frozen_today):
            cls.certificate = cls.env['l10n_mx_edi.certificate'].create({
                'content': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.cer', 'rb').read()),
                'key': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.key', 'rb').read()),
                'password': '12345678a',
                'company_id': cls.company_data['company'].id,
            })
        cls.certificate.write({
            'date_start': '2016-01-01 01:00:00',
            'date_end': '2018-01-01 01:00:00',
        })

        # ==== Business ====
        cls.tax_16 = cls.env["account.chart.template"].ref('tax12')
        cls.tax_16_purchase = cls.env["account.chart.template"].ref('tax14')
        cls.tax_4_purchase_withholding = cls.env["account.chart.template"].ref('tax1')
        cls.tax_0 = cls.env["account.chart.template"].ref('tax9')
        cls.tax_0_exento = cls.tax_0.copy()
        cls.tax_0_exento.l10n_mx_factor_type = 'Exento'
        cls.tax_0_exento_purchase = cls.env["account.chart.template"].ref('tax20')
        cls.tax_8 = cls.env["account.chart.template"].ref('tax17')
        cls.tax_8_ieps = cls.env["account.chart.template"].ref('ieps_8_sale')
        cls.tax_0_ieps = cls.tax_8_ieps.copy(default={'amount': 0.0})
        cls.tax_6_ieps = cls.tax_8_ieps.copy(default={'amount': 6.0})
        cls.tax_7_ieps = cls.tax_8_ieps.copy(default={'amount': 7.0})
        cls.tax_26_5_ieps = cls.env["account.chart.template"].ref('ieps_26_5_sale')
        cls.tax_53_ieps = cls.env["account.chart.template"].ref('ieps_53_sale')
        cls.tax_10_ret_isr = cls.env["account.chart.template"].ref('tax3')
        cls.tax_10_ret_isr.type_tax_use = 'sale'
        cls.tax_10_67_ret = cls.env["account.chart.template"].ref('tax8')
        cls.tax_10_67_ret.type_tax_use = 'sale'
        cls.existing_taxes_combinations_to_test = [
            # pylint: disable=bad-whitespace
            # Line 1                                                Line 2                  Line 3
            (cls.env['account.tax'],),
            (cls.tax_0_exento,                                      cls.tax_0),
            (cls.tax_0_exento,                                      cls.tax_16),
            (cls.tax_0,                                             cls.tax_16),
            (cls.tax_0_exento,                                      cls.tax_0,              cls.tax_16),
            (cls.tax_0_exento,),
            (cls.tax_0,),
            (cls.tax_16 + cls.tax_10_ret_isr + cls.tax_10_67_ret,),
            (cls.tax_8_ieps + cls.tax_0,),
            (cls.tax_53_ieps + cls.tax_16,),
        ]

        cls.product = cls._create_product()

        cls.payment_term = cls.env['account.payment.term'].create({
            'name': 'test l10n_mx_edi',
            'line_ids': [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 90,
            })],
        })

        cls.partner_mx = cls.env['res.partner'].create({
            'name': "INMOBILIARIA CVA",
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'street': "Campobasso Sur 3201 - 9001",
            'city': "Hidalgo del Parral",
            'state_id': cls.env.ref('base.state_mx_chih').id,
            'zip': '33826',
            'country_id': cls.env.ref('base.mx').id,
            'vat': 'ICV060329BY0',
            'bank_ids': [Command.create({'acc_number': "0123456789"})],
            'l10n_mx_edi_fiscal_regime': '601',
        })
        cls.partner_us = cls.env['res.partner'].create({
            'name': 'partner_us',
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'street': "77 Santa Barbara Rd",
            'city': "Pleasant Hill",
            'state_id': cls.env.ref('base.state_us_5').id,
            'zip': '94523',
            'country_id': cls.env.ref('base.us').id,
            'vat': '123456789',
            'bank_ids': [Command.create({'acc_number': "BE01234567890123"})],
        })

        cls.payment_method_efectivo = cls.env.ref('l10n_mx_edi.payment_method_efectivo')

        # Multi-currency setup.
        cls.env['res.currency.rate'].sudo().search([]).unlink()
        cls.usd = cls.env.ref('base.USD')
        cls.usd.active = True
        cls.chf = cls.env.ref('base.CHF')
        cls.chf.active = True
        cls.comp_curr = cls.company_data['currency']

        cls.uuid = 0

    @contextmanager
    def mx_external_setup(self, date_obj):
        """ This must wrap all MX tests and allow to correctly mock the date and to easily
        check the validity of generated files using the web-services instead of mocking everything.
        To "really" test the files, set 'EXTERNAL_MODE' to True.
        That way, the files will be checked by SolucionFactible.

        :param date_obj:    A representation of the time as a datetime object.
        """
        # Ensure the certificate is always valid.
        self.certificate.write({
            'date_start': date_obj - relativedelta(years=2),
            'date_end': date_obj + relativedelta(years=2),
        })

        with freeze_time(date_obj), patch('odoo.tools.zeep.client.SERIALIZABLE_TYPES', SERIALIZABLE_TYPES + (FakeDatetime,)):
            yield

    @contextmanager
    def mocked_retrieve_partner(self, allowed_partners=None):
        """ Mock the res.partner._retrieve_partner method to restrict the result
        to allowed partners inside the sandbox test environment.

        :param allowed_partners:    The allowed partners as a result.
        :return:                    The result of the mocked method.
        """
        super_method = self.env.registry['res.partner']._retrieve_partner

        def retrieve_partner(*args, **kwargs):
            partner = super_method(*args, **kwargs)

            if not allowed_partners or (partner not in allowed_partners):
                return self.env['res.partner']

            return partner

        with patch.object(self.env.registry['res.partner'], '_retrieve_partner', retrieve_partner):
            yield

    @classmethod
    def setup_rates(cls, currency, *rates):
        currency.sudo().rate_ids.unlink()
        return cls.env['res.currency.rate'].create([
            {
                'name': rate_date,
                'rate': rate,
                'currency_id': currency.id,
            }
            for rate_date, rate in rates
        ])

    @contextmanager
    def with_mocked_pac_method(self, method_name, method_replacement):
        """ Helper to mock an rpc call to the PAC.

        :param method_name:         The name of the method to mock.
        :param method_replacement:  The method to be called instead.
        """
        with patch.object(type(self.env['l10n_mx_edi.document']), method_name, method_replacement):
            yield

    def with_mocked_pac_sign_success(self):
        """ Mock the signature method to fake a success response whatever the selected PAC.
        However, if EXTERNAL_MODE is True, the web-service is made using SolFact.
        """
        method_name = f'_{self.env.company.l10n_mx_edi_pac}_sign'

        def fake_success(_record, _credentials, cfdi_str):
            # Inject UUID.
            tree = etree.fromstring(cfdi_str)
            self.uuid += 1
            uuid = f"00000000-0000-0000-0000-{str(self.uuid).rjust(12, '0')}"
            stamp = f"""
                <tfd:TimbreFiscalDigital
                    xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
                    xsi:schemaLocation="http://www.sat.gob.mx/TimbreFiscalDigital http://www.sat.gob.mx/sitio_internet/cfd/TimbreFiscalDigital/TimbreFiscalDigitalv11.xsd"
                    Version="1.1"
                    UUID="{uuid}"
                    FechaTimbrado="___ignore___"
                    NoCertificadoSAT="___ignore___"
                    RfcProvCertif="___ignore___"
                    SelloCFD="___ignore___"
                    SelloSAT="___ignore___"
                />
            """
            complemento_node = tree.xpath("//*[local-name()='Complemento']")
            if complemento_node:
                complemento_node[0].insert(len(tree), etree.fromstring(stamp))
            else:
                complemento_node = f"""
                    <cfdi:Complemento
                        xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
                        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                        xsi:schemaLocation="http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd">
                        {stamp}
                    </cfdi:Complemento>
                """
                tree.insert(len(tree), etree.fromstring(complemento_node))
                tree[-1].attrib.clear()
            cfdi_str = etree.tostring(tree, xml_declaration=True, encoding='UTF-8')

            return {'cfdi_str': cfdi_str}

        if not EXTERNAL_MODE:
            return self.with_mocked_pac_method(method_name, fake_success)

        super_solfact_sign = self.env.registry['l10n_mx_edi.document']._solfact_sign

        def solfact_sign(record, credentials, cfdi_str):
            results = super_solfact_sign(record, credentials, cfdi_str)
            if results.get('errors'):
                raise Exception(pprint.pformat(results['errors']))
            return results

        return self.with_mocked_pac_method('_solfact_sign', solfact_sign)

    def with_mocked_pac_sign_error(self):
        def error(_record, *args, **kwargs):
            return {'errors': ["turlututu"]}

        return self.with_mocked_pac_method(f'_{self.env.company.l10n_mx_edi_pac}_sign', error)

    def with_mocked_pac_cancel_success(self):
        def success(record, *args, **kwargs):
            return {}

        return self.with_mocked_pac_method(f'_{self.env.company.l10n_mx_edi_pac}_cancel', success)

    def with_mocked_pac_cancel_error(self):
        def error(record, *args, **kwargs):
            return {'errors': ["turlututu"]}

        return self.with_mocked_pac_method(f'_{self.env.company.l10n_mx_edi_pac}_cancel', error)

    @contextmanager
    def with_mocked_sat_call(self, sat_state_method):
        """ Helper to mock an rpc call to the SAT.

        :param sat_state_method: A method taking a document as parameter and returning the expected sat_state.
        """
        def fetch_sat_status(document, *args, **kwargs):
            return {'value': sat_state_method(document)}

        def update_sat_state(document, *args, **kwargs):
            document.sat_state = sat_state_method(document)

        Document = self.env.registry['l10n_mx_edi.document']
        if self.env.company.l10n_mx_edi_pac_test_env:
            # In test mode, we only want to check if the SAT button updates the right documents and if the
            # global sat_state is well computed. We don't want to create on-the-fly a new cancel document.
            # This can't be tested on the UI and there is no way to force the return of the SAT api.
            with patch.object(Document, '_update_sat_state', update_sat_state):
                yield
        else:
            with patch.object(Document, '_fetch_sat_status', fetch_sat_status):
                yield

    @contextmanager
    def with_mocked_global_invoice_sequence(self, number):
        sequence = self.env['l10n_mx_edi.document']._get_global_invoice_cfdi_sequence(self.env.company)
        sequence.number_next = number
        yield

    def _test_cfdi_rounding(self, run_function):
        for tax_calculation_rounding_method in ('round_per_line', 'round_globally'):
            with self.subTest(tax_calculation_rounding_method=tax_calculation_rounding_method):
                self.env.company.tax_calculation_rounding_method = tax_calculation_rounding_method
                run_function(tax_calculation_rounding_method)

    @classmethod
    def _create_product(cls, **kwargs):
        return cls.env['product.product'].create({
            'name': 'product_mx',
            'weight': 2,
            'default_code': "product_mx",
            'uom_po_id': cls.env.ref('uom.product_uom_kgm').id,
            'uom_id': cls.env.ref('uom.product_uom_kgm').id,
            'lst_price': 1000.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'unspsc_code_id': cls.env.ref('product_unspsc.unspsc_code_01010101').id,
            'taxes_id': [Command.set(cls.tax_16.ids)],
            'company_id': cls.env.company.id,
            **kwargs,
        })

    def _create_invoice(self, **kwargs):
        today = fields.Date.today()
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_mx.id,
            'date': today,
            'invoice_date': today,
            'invoice_date_due': today + relativedelta(days=40),  # PPD by default
            'l10n_mx_edi_payment_method_id': self.payment_method_efectivo.id,
            'currency_id': self.comp_curr.id,
            'invoice_line_ids': [Command.create({'product_id': self.product.id})],
            **kwargs,
        })
        invoice.action_post()
        return invoice

    def _create_invoice_with_amount(self, invoice_date, currency, amount):
        return self._create_invoice(
            invoice_date=invoice_date,
            date=invoice_date,
            currency_id=currency.id,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': amount,
                    'tax_ids': [],
                }),
            ],
        )

    def _create_payment(self, invoices, **kwargs):
        return self.env['account.payment.register']\
            .with_context(
                active_model='account.move',
                active_ids=invoices.ids,
            )\
            .create({
                'group_payment': True,
                **kwargs,
            })\
            ._create_payments()

    def _assert_document_cfdi(self, document, filename):
        file_path = f'{self.test_module}/tests/test_files/{filename}.xml'
        with misc.file_open(file_path, 'rb') as file:
            expected_cfdi = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(document.attachment_id.raw),
            self.get_xml_tree_from_string(expected_cfdi),
        )

    def _assert_invoice_cfdi(self, invoice, filename):
        document = invoice.l10n_mx_edi_invoice_document_ids.filtered(lambda x: x.state == 'invoice_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)

    def _assert_invoice_payment_cfdi(self, payment, filename):
        document = payment.l10n_mx_edi_payment_document_ids.filtered(lambda x: x.state == 'payment_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)

    def _assert_global_invoice_cfdi_from_invoices(self, invoices, filename):
        document = invoices.l10n_mx_edi_invoice_document_ids.filtered(lambda x: x.state == 'ginvoice_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)

    def _upload_document_on_journal(self, journal, content, filename):
        attachment = self.env['ir.attachment'].create({
            'raw': content,
            'name': filename,
        })
        action_vals = journal.create_document_from_attachment(attachment.ids)
        return self.env['account.move'].browse(action_vals['res_id'])


class TestMxEdiCommonExternal(TestMxEdiCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='mx'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        try:
            with freeze_time(cls.frozen_today):
                cls.certificate = cls.env['l10n_mx_edi.certificate'].create({
                    'content': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.cer', 'rb').read()),
                    'key': base64.encodebytes(misc.file_open('l10n_mx_edi/demo/pac_credentials/certificate.key', 'rb').read()),
                    'password': '12345678a',
                    'company_id': cls.env.company.id,
                })
        except ValidationError:
            raise SkipTest("CFDI certificate is invalid.")
