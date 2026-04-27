# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from datetime import datetime
from lxml import etree
from pprint import pformat
from unittest import mock

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged
from odoo.tools.xml_utils import cleanup_xml_node
from odoo import Command
from pytz import timezone
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEcEdiCommon(AccountEdiTestCommon):

    @classmethod
    @AccountEdiTestCommon.setup_country('ec')
    @AccountEdiTestCommon.setup_edi_format('l10n_ec_edi.ecuadorian_edi_format')
    def setUpClass(cls):
        super().setUpClass()

        cls.frozen_today = datetime(year=2022, month=1, day=25, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        # ==== Config ====
        cls.company_data['company'].write({
            'name': "EC Test Company",
            'vat': "1792366836001",
            'street': "Avenida Machala 42",
            'zip': "090514",
            'city': "Guayaquil",
            'country_id': cls.env.ref('base.ec').id,
            'l10n_ec_legal_name': "EC Test Company (official)",
        })

        for journal in (cls.company_data['default_journal_sale'], cls.company_data['default_journal_purchase']):
            # Needs to be set before assigning authorization number
            journal.write({
                'l10n_latam_use_documents': True, # For tests the value is not set automatically
                'l10n_ec_entity': '001',
                'l10n_ec_emission': '001',
                'l10n_ec_emission_address_id': cls.company_data['company'].partner_id,
            })

        # ==== Business ====
        partner_vals = {
            'name': "EC Test Partner AàÁ³$£€èêÈÊöÔÇç¡⅛&@™",  # special characters should be escaped appropriately
            'street': "Av. Libertador Simón Bolívar 1155",
            'zip': "170209",
            'city': "Quito",
            'country_id': cls.env.ref('base.ec').id,
        }
        cls.partner_a.write({
            **partner_vals,
            'vat': "0453661050152",
            'l10n_latam_identification_type_id': cls.env.ref('l10n_ec.ec_ruc').id,
        })

        cls.partner_b.write({
            **partner_vals,
            'vat': "0453661050",
            'l10n_latam_identification_type_id': cls.env.ref('l10n_ec.ec_dni').id,
        })
        cls.product_withhold = cls.env['product.product'].create({
            'name': 'Test Service Product',
            'type': 'service',
            'lst_price': 100.0,
            'standard_price': 80.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [(Command.set(cls.tax_sale_a.ids))],
            'supplier_taxes_id': [Command.set(cls.tax_purchase_a.ids)],
            'l10n_ec_withhold_tax_id': cls._get_tax_by_xml_id('tax_withhold_profit_312').id,
        })

    # ===== HELPER METHODS =====

    @classmethod
    def _get_tax_by_xml_id(cls, trailing_xml_id):
        """ Helper to retrieve a tax easily.
        :param trailing_xml_id: The trailing tax's xml id.
        :return:                An account.tax record
        """
        return cls.env.ref(f'account.{cls.env.company.id}_{trailing_xml_id}')

    def get_invoice_line_vals(self, vat_tax_xmlid='tax_vat_510_sup_01'):
        """Default values for invoice line creation"""
        return [Command.create({
            'product_id': self.product_a.id,
            'price_unit': 100.0,
            'quantity': 5,
            'discount': 20,
            'tax_ids': [Command.set(self._get_tax_by_xml_id(vat_tax_xmlid).ids)],
        })]

    def get_invoice_vals(self, invoice_line_args):
        """Default values for invoice creation"""
        return {
            'name': 'INV/01',
            'invoice_date': self.frozen_today,
            'date': self.frozen_today,
            'invoice_line_ids': invoice_line_args,
            'l10n_ec_sri_payment_id': self.env['l10n_ec.sri.payment'].search([('code', '=', 16)], limit=1).id,  # Debit card (see l10n_ec.sri.payment.csv)
            'l10n_latam_document_number': '001-001-000000001',
        }

    def get_invoice(self, invoice_args, invoice_line_args=None):
        if invoice_line_args is None:
            invoice_line_args = self.get_invoice_line_vals()
        invoice_vals = self.get_invoice_vals(invoice_line_args)
        invoice_vals.update(invoice_args)
        invoice = self.env['account.move'].create({
            **invoice_vals,
        })
        invoice.l10n_latam_document_number = invoice.l10n_latam_document_number or '001-001-000000001'
        return invoice

    def get_custom_purchase_invoice_line_vals(self):
        product_ids_vals = [
            (self.product_a, 'tax_vat_510_sup_01', 100.0, 5.0, 20.0),
            (self.product_b, 'tax_vat_512_sup_04', 100.0, 5.0, 0.0),
            (self.product_withhold, 'tax_vat_517_sup_15', 50.0, 1.0, 0.0),
            (self.product_withhold, 'tax_vat_517_sup_15', 30.0, 10.0, 0.0)
        ]
        line_vals = []
        for product, tax, price_unit, qty, discount in product_ids_vals:
            line_vals.append(Command.create({
                'product_id': product.id,
                'price_unit': price_unit,
                'quantity': qty,
                'tax_ids': [Command.set(self._get_tax_by_xml_id(tax).ids)],
                'discount': discount,
            }))
        return line_vals

    def get_liquidation_invoice_line_vals(self, same_tax=False):
        # Lines with 2 taxes in order to validate reimbursements
        second_tax_xml_id = (same_tax and 'tax_vat_510_sup_01') or 'tax_vat_517_sup_07'
        return [
            Command.create({
                'product_id': self.product_a.id,
                'price_unit': 10.0,
                'quantity': 1.0,
                'discount': 0.0,
                'tax_ids': [Command.set(self._get_tax_by_xml_id('tax_vat_510_sup_01').ids)],
            }),
            Command.create({
                'product_id': self.product_b.id,
                'price_unit': 10.0,
                'quantity': 1.0,
                'discount': 0.0,
                'tax_ids': [Command.set(self._get_tax_by_xml_id(second_tax_xml_id).ids)],
            })]

    def get_wizard_and_purchase_invoice(self):
        purchase_journal = self.env['account.journal'].search([
            ('company_id', '=', self.company_data['company'].id),
            ('code', '=', 'BILL')])
        with freeze_time(self.frozen_today):
            purchase_invoice = self.get_invoice({
                'move_type': 'in_invoice',
                'partner_id': self.partner_a.id,
                'journal_id': purchase_journal.id,
                'l10n_ec_sri_payment_id': self.env.ref('l10n_ec.P1').id,
                'invoice_line_ids': self.get_custom_purchase_invoice_line_vals(),
            })
        purchase_invoice.action_post()
        with freeze_time(self.frozen_today):
            wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=[purchase_invoice.id], active_model='account.move').create({})
            wizard.document_number = '001-001-000000001'
        return wizard, purchase_invoice

    def set_custom_taxpayer_type_on_partner_a(self):
        # Setting a contributor type to partner
        self.partner_a.l10n_ec_taxpayer_type_id = self.env.ref('l10n_ec_edi.l10n_ec_taxpayer_type_01')
        self.partner_a.l10n_ec_taxpayer_type_id.profit_withhold_tax_id = self._get_tax_by_xml_id('tax_withhold_profit_303')
        self.partner_a.l10n_ec_taxpayer_type_id.vat_goods_withhold_tax_id = self._get_tax_by_xml_id('tax_withhold_vat_10')
        self.partner_a.l10n_ec_taxpayer_type_id.vat_services_withhold_tax_id = self._get_tax_by_xml_id('tax_withhold_vat_20')

    @contextmanager
    def mock_zeep_client(self, expected_operations):
        """ A context manager to mock the API calls made by the EDI:
            - set `l10n_ec_production_env = True` on the active company
            - mock zeep.Client in `l10n_ec_edi.models.account_edi_format`
            - mock `env['account.edi.format']._l10n_ec_generate_signed_xml`

        :param expected_operations: a list of expected endpoint calls, each call being a tuple
                                    (endpoint, expected_kwargs, response) indicating the expected endpoint called,
                                    the expected endpoint parameters and the response to serve.
        """
        class MockedReturnValue:
            def __init__(self, **kwargs):
                self.__dict = kwargs

            def __getitem__(self, key):
                return self.__dict[key]

            def __getattr__(self, name):
                return self.__dict[name]

        class MockedService:
            def __init__(self, test_case, expected_operations):
                self.test_case = test_case
                self.expected_operations_enum = enumerate(expected_operations, start=1)

                def create_endpoint(endpoint: str):
                    def call_endpoint(**kwargs):
                        idx, (expected_endpoint, expected_kwargs, response) = next(self.expected_operations_enum)
                        test_case.assertEqual(
                            endpoint,
                            expected_endpoint,
                            f"Operation {idx} called `{endpoint}` but should have called `{expected_endpoint}`"
                        )
                        test_case.assertEqual(kwargs, expected_kwargs, f"Operation {idx}: request did not match expected")
                        return MockedReturnValue(**response)

                    return call_endpoint

                self.autorizacionComprobante = create_endpoint('autorizacionComprobante')
                self.validarComprobante = create_endpoint('validarComprobante')

            def assert_all_endpoints_called(self):
                remaining_operations = list(self.expected_operations_enum)

                if remaining_operations:
                    self.test_case.fail(f'Not all endpoint calls were made! Remaining calls:\n{pformat(remaining_operations)}')

        mocked_service = MockedService(self, expected_operations)

        class MockedClient:
            def __init__(self, wsdl, timeout):
                self.service = mocked_service

        def mocked_l10n_ec_generate_signed_xml(self, company_id, xml_node_or_string):
            return etree.tostring(cleanup_xml_node(xml_node_or_string), encoding='unicode')

        # We set this to True in order to mock sending invoices to SRI
        old_l10n_ec_production_env = self.env.company.l10n_ec_production_env
        self.env.company.l10n_ec_production_env = True

        with (
            mock.patch('odoo.addons.l10n_ec_edi.models.account_edi_format.Client', new=MockedClient),
            mock.patch.object(
                self.env['account.edi.format'].__class__,
                '_l10n_ec_generate_signed_xml',
                new=mocked_l10n_ec_generate_signed_xml,
            ),
        ):
            yield

        mocked_service.assert_all_endpoints_called()
        self.env.company.l10n_ec_production_env = old_l10n_ec_production_env


# ===== HARD-CODED XMLS =====

L10N_EC_EDI_XML_OUT_INV = """
<factura version="2.1.0" id="comprobante">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>PRUEBAS SERVICIO DE RENTAS INTERNAS</razonSocial>
        <nombreComercial>PRUEBAS SERVICIO DE RENTAS INTERNAS</nombreComercial>
        <ruc>1792366836001</ruc>
        <claveAcceso>2501202201179236683600110010010000000013121521410</claveAcceso>
        <codDoc>01</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>000000001</secuencial>
        <dirMatriz>Avenida Machala 42</dirMatriz>
    </infoTributaria>
    <infoFactura>
        <fechaEmision>25/01/2022</fechaEmision>
        <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>
        <obligadoContabilidad>SI</obligadoContabilidad>
        <tipoIdentificacionComprador>04</tipoIdentificacionComprador>
        <razonSocialComprador>EC Test Partner AàÁ³$£€èêÈÊöÔÇç¡⅛&amp;@™</razonSocialComprador>
        <identificacionComprador>0453661050152</identificacionComprador>
        <direccionComprador>Av. Libertador Simón Bolívar 1155</direccionComprador>
        <totalSinImpuestos>400.000000</totalSinImpuestos>
        <totalDescuento>100.00</totalDescuento>
        <totalConImpuestos>
            <totalImpuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>2</codigoPorcentaje>
                <baseImponible>400.000000</baseImponible>
                <tarifa>12.000000</tarifa>
                <valor>48.00</valor>
            </totalImpuesto>
        </totalConImpuestos>
        <importeTotal>448.00</importeTotal>
        <moneda>DOLAR</moneda>
        <pagos>
            <pago>
                <formaPago>16</formaPago>
                <total>448.00</total>
                <plazo>0</plazo>
                <unidadTiempo>dias</unidadTiempo>
            </pago>
        </pagos>
    </infoFactura>
    <detalles>
        <detalle>
            <codigoPrincipal>N/A</codigoPrincipal>
            <descripcion>product_a</descripcion>
            <cantidad>5.000000</cantidad>
            <precioUnitario>100.000000</precioUnitario>
            <descuento>100.00</descuento>
            <precioTotalSinImpuesto>400.00</precioTotalSinImpuesto>
            <impuestos>
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <tarifa>12.000000</tarifa>
                    <baseImponible>400.000000</baseImponible>
                    <valor>48.00</valor>
                </impuesto>
            </impuestos>
        </detalle>
    </detalles>
    <infoAdicional>
        <campoAdicional nombre="Referencia">Fact 001-001-000000001</campoAdicional>
        <campoAdicional nombre="Vendedor">Because I am accountman!</campoAdicional>
        <campoAdicional nombre="E-mail">accountman@test.com</campoAdicional>
    </infoAdicional>
</factura>""".encode()

L10N_EC_EDI_XML_DEBIT_NOTE = """
<notaDebito version="1.0.0" id="comprobante">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>PRUEBAS SERVICIO DE RENTAS INTERNAS</razonSocial>
        <nombreComercial>PRUEBAS SERVICIO DE RENTAS INTERNAS</nombreComercial>
        <ruc>1792366836001</ruc>
        <claveAcceso>2501202205179236683600110010010000000013121521416</claveAcceso>
        <codDoc>05</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>000000001</secuencial>
        <dirMatriz>Avenida Machala 42</dirMatriz>
    </infoTributaria>
    <infoNotaDebito>
        <fechaEmision>25/01/2022</fechaEmision>
        <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>
        <tipoIdentificacionComprador>04</tipoIdentificacionComprador>
        <razonSocialComprador>EC Test Partner AàÁ³$£€èêÈÊöÔÇç¡⅛&amp;@™</razonSocialComprador>
        <identificacionComprador>0453661050152</identificacionComprador>
        <obligadoContabilidad>SI</obligadoContabilidad>
        <codDocModificado>01</codDocModificado>
        <numDocModificado>001-001-000000001</numDocModificado>
        <fechaEmisionDocSustento>25/01/2022</fechaEmisionDocSustento>
        <totalSinImpuestos>400.000000</totalSinImpuestos>
        <impuestos>
            <impuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>2</codigoPorcentaje>
                <tarifa>12.000000</tarifa>
                <baseImponible>400.000000</baseImponible>
                <valor>48.00</valor>
            </impuesto>
        </impuestos>
        <valorTotal>448.00</valorTotal>
        <pagos>
            <pago>
                <formaPago>16</formaPago>
                <total>448.00</total>
                <plazo>0</plazo>
                <unidadTiempo>dias</unidadTiempo>
            </pago>
        </pagos>
    </infoNotaDebito>
    <motivos>
        <motivo>
            <razon>product_a</razon>
            <valor>400.000000</valor>
        </motivo>
    </motivos>
    <infoAdicional>
        <campoAdicional nombre="Referencia">NotDb 001-001-000000001</campoAdicional>
        <campoAdicional nombre="Vendedor">Because I am accountman!</campoAdicional>
        <campoAdicional nombre="E-mail">accountman@test.com</campoAdicional>
    </infoAdicional>
</notaDebito>""".encode()

L10N_EC_EDI_XML_CREDIT_NOTE = """
<notaCredito version="1.1.0" id="comprobante">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>PRUEBAS SERVICIO DE RENTAS INTERNAS</razonSocial>
        <nombreComercial>PRUEBAS SERVICIO DE RENTAS INTERNAS</nombreComercial>
        <ruc>1792366836001</ruc>
        <claveAcceso>2501202204179236683600110010010000000013121521411</claveAcceso>
        <codDoc>04</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>000000001</secuencial>
        <dirMatriz>Avenida Machala 42</dirMatriz>
    </infoTributaria>
    <infoNotaCredito>
        <fechaEmision>25/01/2022</fechaEmision>
        <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>
        <tipoIdentificacionComprador>04</tipoIdentificacionComprador>
        <razonSocialComprador>EC Test Partner AàÁ³$£€èêÈÊöÔÇç¡⅛&amp;@™</razonSocialComprador>
        <identificacionComprador>0453661050152</identificacionComprador>
        <obligadoContabilidad>SI</obligadoContabilidad>
        <codDocModificado>01</codDocModificado>
        <numDocModificado>001-001-000000001</numDocModificado>
        <fechaEmisionDocSustento>25/01/2022</fechaEmisionDocSustento>
        <totalSinImpuestos>400.000000</totalSinImpuestos>
        <valorModificacion>448.00</valorModificacion>
        <moneda>DOLAR</moneda>
        <totalConImpuestos>
            <totalImpuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>2</codigoPorcentaje>
                <baseImponible>400.000000</baseImponible>
                <valor>48.00</valor>
            </totalImpuesto>
        </totalConImpuestos>
        <motivo>NotCr 001-001-000000001</motivo>
    </infoNotaCredito>
    <detalles>
        <detalle>
            <codigoInterno>N/A</codigoInterno>
            <descripcion>product_a</descripcion>
            <cantidad>5.000000</cantidad>
            <precioUnitario>100.000000</precioUnitario>
            <descuento>100.00</descuento>
            <precioTotalSinImpuesto>400.00</precioTotalSinImpuesto>
            <impuestos>
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <tarifa>12.000000</tarifa>
                    <baseImponible>400.000000</baseImponible>
                    <valor>48.00</valor>
                </impuesto>
            </impuestos>
        </detalle>
    </detalles>
    <infoAdicional>
        <campoAdicional nombre="Referencia">NotCr 001-001-000000001</campoAdicional>
        <campoAdicional nombre="Vendedor">Because I am accountman!</campoAdicional>
        <campoAdicional nombre="E-mail">accountman@test.com</campoAdicional>
    </infoAdicional>
</notaCredito>""".encode()

L10N_EC_EDI_XML_PURCHASE_LIQ = """
<liquidacionCompra version="1.1.0" id="comprobante">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>PRUEBAS SERVICIO DE RENTAS INTERNAS</razonSocial>
        <nombreComercial>PRUEBAS SERVICIO DE RENTAS INTERNAS</nombreComercial>
        <ruc>1792366836001</ruc>
        <claveAcceso>2501202203179236683600110010010000000013121521413</claveAcceso>
        <codDoc>03</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>000000001</secuencial>
        <dirMatriz>Avenida Machala 42</dirMatriz>
    </infoTributaria>
    <infoLiquidacionCompra>
        <fechaEmision>25/01/2022</fechaEmision>
        <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>
        <obligadoContabilidad>SI</obligadoContabilidad>
        <tipoIdentificacionProveedor>05</tipoIdentificacionProveedor>
        <razonSocialProveedor>EC Test Partner AàÁ³$£€èêÈÊöÔÇç¡⅛&amp;@™</razonSocialProveedor>
        <identificacionProveedor>0453661050</identificacionProveedor>
        <direccionProveedor>Av. Libertador Simón Bolívar 1155</direccionProveedor>
        <totalSinImpuestos>400.000000</totalSinImpuestos>
        <totalDescuento>100.00</totalDescuento>
        <totalConImpuestos>
            <totalImpuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>2</codigoPorcentaje>
                <baseImponible>400.000000</baseImponible>
                <valor>48.00</valor>
            </totalImpuesto>
        </totalConImpuestos>
        <importeTotal>448.00</importeTotal>
        <moneda>DOLAR</moneda>
        <pagos>
            <pago>
                <formaPago>16</formaPago>
                <total>134.40</total>
                <plazo>0</plazo>
                <unidadTiempo>dias</unidadTiempo>
            </pago>
            <pago>
                <formaPago>16</formaPago>
                <total>313.60</total>
                <plazo>34</plazo>
                <unidadTiempo>dias</unidadTiempo>
            </pago>
        </pagos>
    </infoLiquidacionCompra>
    <detalles>
        <detalle>
            <codigoPrincipal>N/A</codigoPrincipal>
            <descripcion>product_a</descripcion>
            <cantidad>5.000000</cantidad>
            <precioUnitario>100.000000</precioUnitario>
            <descuento>100.00</descuento>
            <precioTotalSinImpuesto>400.00</precioTotalSinImpuesto>
            <impuestos>
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <tarifa>12.000000</tarifa>
                    <baseImponible>400.000000</baseImponible>
                    <valor>48.00</valor>
                </impuesto>
            </impuestos>
        </detalle>
    </detalles>
    <infoAdicional>
        <campoAdicional nombre="Referencia">LiqCo 001-001-000000001</campoAdicional>
    </infoAdicional>
</liquidacionCompra>""".encode()

L10N_EC_EDI_XML_IN_WTH = """
<comprobanteRetencion version="2.0.0" id="comprobante">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>PRUEBAS SERVICIO DE RENTAS INTERNAS</razonSocial>
        <nombreComercial>PRUEBAS SERVICIO DE RENTAS INTERNAS</nombreComercial>
        <ruc>1792366836001</ruc>
        <claveAcceso>2501202207179236683600110010010000000013121521419</claveAcceso>
        <codDoc>07</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>000000001</secuencial>
        <dirMatriz>Avenida Machala 42</dirMatriz>
    </infoTributaria>
    <infoCompRetencion>
        <fechaEmision>25/01/2022</fechaEmision>
        <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>
        <obligadoContabilidad>SI</obligadoContabilidad>
        <tipoIdentificacionSujetoRetenido>04</tipoIdentificacionSujetoRetenido>
        <parteRel>NO</parteRel>
        <razonSocialSujetoRetenido>EC Test Partner AàÁ³$£€èêÈÊöÔÇç¡⅛&amp;@™</razonSocialSujetoRetenido>
        <identificacionSujetoRetenido>0453661050152</identificacionSujetoRetenido>
        <periodoFiscal>01/2022</periodoFiscal>
    </infoCompRetencion>
    <docsSustento>
        <docSustento>
            <codSustento>01</codSustento>
            <codDocSustento>01</codDocSustento>
            <numDocSustento>001001000000001</numDocSustento>
            <fechaEmisionDocSustento>25/01/2022</fechaEmisionDocSustento>
            <pagoLocExt>01</pagoLocExt>
            <totalSinImpuestos>400.00</totalSinImpuestos>
            <importeTotal>448.00</importeTotal>
            <impuestosDocSustento>
                <impuestoDocSustento>
                    <codImpuestoDocSustento>2</codImpuestoDocSustento>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <baseImponible>400.00</baseImponible>
                    <tarifa>12.00</tarifa>
                    <valorImpuesto>48.00</valorImpuesto>
                </impuestoDocSustento>
            </impuestosDocSustento>
            <retenciones>
                <retencion>
                    <codigo>1</codigo>
                    <codigoRetencion>312</codigoRetencion>
                    <baseImponible>400.00</baseImponible>
                    <porcentajeRetener>2.00</porcentajeRetener>
                    <valorRetenido>8.00</valorRetenido>
                </retencion>
            </retenciones>
            <pagos>
                <pago>
                    <formaPago>01</formaPago>
                    <total>448.00</total>
                </pago>
            </pagos>
        </docSustento>
    </docsSustento>
    <infoAdicional>
        <campoAdicional nombre="Direccion">Av. Libertador Simón Bolívar 1155</campoAdicional>
    </infoAdicional>
</comprobanteRetencion>""".encode()

L10N_EC_EDI_XML_PURCHASE_LIQ_WTH = """
<comprobanteRetencion version="2.0.0" id="comprobante">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>PRUEBAS SERVICIO DE RENTAS INTERNAS</razonSocial>
        <nombreComercial>PRUEBAS SERVICIO DE RENTAS INTERNAS</nombreComercial>
        <ruc>1792366836001</ruc>
        <claveAcceso>2501202207179236683600110010010000000013121521419</claveAcceso>
        <codDoc>07</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>000000001</secuencial>
        <dirMatriz>Avenida Machala 42</dirMatriz>
    </infoTributaria>
    <infoCompRetencion>
        <fechaEmision>25/01/2022</fechaEmision>
        <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>
        <obligadoContabilidad>SI</obligadoContabilidad>
        <tipoIdentificacionSujetoRetenido>05</tipoIdentificacionSujetoRetenido>
        <parteRel>NO</parteRel>
        <razonSocialSujetoRetenido>EC Test Partner AàÁ³$£€èêÈÊöÔÇç¡⅛&amp;@™</razonSocialSujetoRetenido>
        <identificacionSujetoRetenido>0453661050</identificacionSujetoRetenido>
        <periodoFiscal>01/2022</periodoFiscal>
    </infoCompRetencion>
    <docsSustento>
        <docSustento>
            <codSustento>01</codSustento>
            <codDocSustento>03</codDocSustento>
            <numDocSustento>001001000000001</numDocSustento>
            <fechaEmisionDocSustento>25/01/2022</fechaEmisionDocSustento>
            <pagoLocExt>01</pagoLocExt>
            <totalSinImpuestos>100.00</totalSinImpuestos>
            <importeTotal>112.00</importeTotal>
            <impuestosDocSustento>
                <impuestoDocSustento>
                    <codImpuestoDocSustento>2</codImpuestoDocSustento>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <baseImponible>100.00</baseImponible>
                    <tarifa>12.00</tarifa>
                    <valorImpuesto>12.00</valorImpuesto>
                </impuestoDocSustento>
            </impuestosDocSustento>
            <retenciones>
                <retencion>
                    <codigo>2</codigo>
                    <codigoRetencion>3</codigoRetencion>
                    <baseImponible>12.00</baseImponible>
                    <porcentajeRetener>100.00</porcentajeRetener>
                    <valorRetenido>12.00</valorRetenido>
                </retencion>
            </retenciones>
            <pagos>
                <pago>
                    <formaPago>16</formaPago>
                    <total>112.00</total>
                </pago>
            </pagos>
        </docSustento>
        <docSustento>
            <codSustento>04</codSustento>
            <codDocSustento>03</codDocSustento>
            <numDocSustento>001001000000001</numDocSustento>
            <fechaEmisionDocSustento>25/01/2022</fechaEmisionDocSustento>
            <pagoLocExt>01</pagoLocExt>
            <totalSinImpuestos>200.00</totalSinImpuestos>
            <importeTotal>224.00</importeTotal>
            <impuestosDocSustento>
                <impuestoDocSustento>
                    <codImpuestoDocSustento>2</codImpuestoDocSustento>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <baseImponible>200.00</baseImponible>
                    <tarifa>12.00</tarifa>
                    <valorImpuesto>24.00</valorImpuesto>
                </impuestoDocSustento>
            </impuestosDocSustento>
            <retenciones>
                <retencion>
                    <codigo>2</codigo>
                    <codigoRetencion>3</codigoRetencion>
                    <baseImponible>23.99</baseImponible>
                    <porcentajeRetener>100.00</porcentajeRetener>
                    <valorRetenido>23.99</valorRetenido>
                </retencion>
            </retenciones>
            <pagos>
                <pago>
                    <formaPago>16</formaPago>
                    <total>224.00</total>
                </pago>
            </pagos>
        </docSustento>
    </docsSustento>
    <infoAdicional>
        <campoAdicional nombre="Direccion">Av. Libertador Simón Bolívar 1155</campoAdicional>
    </infoAdicional>
</comprobanteRetencion>""".encode()

L10N_EC_EDI_XPATH_INVOICE_IN = """
<xpath expr="//docsSustento" position="replace">
    <docsSustento>
        <docSustento>
            <codSustento>01</codSustento>
            <codDocSustento>01</codDocSustento>
            <numDocSustento>001001000000001</numDocSustento>
            <fechaEmisionDocSustento>25/01/2022</fechaEmisionDocSustento>
            <pagoLocExt>01</pagoLocExt>
            <totalSinImpuestos>400.00</totalSinImpuestos>
            <importeTotal>448.00</importeTotal>
            <impuestosDocSustento>
                <impuestoDocSustento>
                    <codImpuestoDocSustento>2</codImpuestoDocSustento>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <baseImponible>400.00</baseImponible>
                    <tarifa>12.00</tarifa>
                    <valorImpuesto>48.00</valorImpuesto>
                </impuestoDocSustento>
            </impuestosDocSustento>
            <retenciones>
                <retencion>
                <codigo>1</codigo>
                <codigoRetencion>312</codigoRetencion>
                <baseImponible>400.00</baseImponible>
                <porcentajeRetener>2.00</porcentajeRetener>
                <valorRetenido>8.00</valorRetenido>
                </retencion>
            </retenciones>
            <pagos>
                <pago>
                <formaPago>01</formaPago>
                <total>448.00</total>
                </pago>
            </pagos>
        </docSustento>
        <docSustento>
            <codSustento>04</codSustento>
            <codDocSustento>01</codDocSustento>
            <numDocSustento>001001000000001</numDocSustento>
            <fechaEmisionDocSustento>25/01/2022</fechaEmisionDocSustento>
            <pagoLocExt>01</pagoLocExt>
            <totalSinImpuestos>500.00</totalSinImpuestos>
            <importeTotal>560.00</importeTotal>
            <impuestosDocSustento>
                <impuestoDocSustento>
                    <codImpuestoDocSustento>2</codImpuestoDocSustento>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <baseImponible>500.00</baseImponible>
                    <tarifa>12.00</tarifa>
                    <valorImpuesto>60.00</valorImpuesto>
                </impuestoDocSustento>
            </impuestosDocSustento>
            <retenciones>
                <retencion>
                <codigo>1</codigo>
                <codigoRetencion>312</codigoRetencion>
                <baseImponible>500.00</baseImponible>
                <porcentajeRetener>2.00</porcentajeRetener>
                <valorRetenido>10.00</valorRetenido>
                </retencion>
            </retenciones>
            <pagos>
                <pago>
                <formaPago>01</formaPago>
                <total>560.00</total>
                </pago>
            </pagos>
        </docSustento>
        <docSustento>
            <codSustento>15</codSustento>
            <codDocSustento>01</codDocSustento>
            <numDocSustento>001001000000001</numDocSustento>
            <fechaEmisionDocSustento>25/01/2022</fechaEmisionDocSustento>
            <pagoLocExt>01</pagoLocExt>
            <totalSinImpuestos>350.00</totalSinImpuestos>
            <importeTotal>350.00</importeTotal>
            <impuestosDocSustento>
                <impuestoDocSustento>
                    <codImpuestoDocSustento>2</codImpuestoDocSustento>
                    <codigoPorcentaje>0</codigoPorcentaje>
                    <baseImponible>350.00</baseImponible>
                    <tarifa>0.00</tarifa>
                    <valorImpuesto>0.00</valorImpuesto>
                </impuestoDocSustento>
            </impuestosDocSustento>
            <retenciones>
                <retencion>
                <codigo>1</codigo>
                <codigoRetencion>312</codigoRetencion>
                <baseImponible>350.00</baseImponible>
                <porcentajeRetener>1.75</porcentajeRetener>
                <valorRetenido>6.13</valorRetenido>
                </retencion>
            </retenciones>
            <pagos>
                <pago>
                <formaPago>01</formaPago>
                <total>350.00</total>
                </pago>
            </pagos>
        </docSustento>
    </docsSustento>
</xpath>
"""

L10N_EC_EDI_XPATH_INVOICE_IN_CUSTOM_TAXPAYER = """
<xpath expr="//docsSustento/docSustento[1]/retenciones" position="replace">
    <retenciones>
        <retencion>
            <codigo>1</codigo>
            <codigoRetencion>303</codigoRetencion>
            <baseImponible>400.00</baseImponible>
            <porcentajeRetener>10.00</porcentajeRetener>
            <valorRetenido>40.00</valorRetenido>
        </retencion>
        <retencion>
            <codigo>2</codigo>
            <codigoRetencion>9</codigoRetencion>
            <baseImponible>48.00</baseImponible>
            <porcentajeRetener>10.00</porcentajeRetener>
            <valorRetenido>4.80</valorRetenido>
        </retencion>
    </retenciones>
</xpath>
<xpath expr="//docsSustento/docSustento[2]/retenciones" position="replace">
    <retenciones>
        <retencion>
            <codigo>1</codigo>
            <codigoRetencion>303</codigoRetencion>
            <baseImponible>500.00</baseImponible>
            <porcentajeRetener>10.00</porcentajeRetener>
            <valorRetenido>50.00</valorRetenido>
        </retencion>
        <retencion>
            <codigo>2</codigo>
            <codigoRetencion>9</codigoRetencion>
            <baseImponible>60.00</baseImponible>
            <porcentajeRetener>10.00</porcentajeRetener>
            <valorRetenido>6.00</valorRetenido>
        </retencion>
    </retenciones>
</xpath>
<xpath expr="//docsSustento/docSustento[3]/retenciones" position="replace">
    <retenciones>
        <retencion>
            <codigo>1</codigo>
            <codigoRetencion>303</codigoRetencion>
            <baseImponible>350.00</baseImponible>
            <porcentajeRetener>10.00</porcentajeRetener>
            <valorRetenido>35.00</valorRetenido>
        </retencion>
    </retenciones>
</xpath>
"""

L10N_EC_EDI_REIMBURSEMENT_LIQUIDATION = """
<liquidacionCompra version="1.1.0" id="comprobante">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>PRUEBAS SERVICIO DE RENTAS INTERNAS</razonSocial>
        <nombreComercial>PRUEBAS SERVICIO DE RENTAS INTERNAS</nombreComercial>
        <ruc>1792366836001</ruc>
        <claveAcceso>2501202203179236683600110010010000000013121521413</claveAcceso>
        <codDoc>03</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>000000001</secuencial>
        <dirMatriz>Avenida Machala 42</dirMatriz>
    </infoTributaria>
    <infoLiquidacionCompra>
        <fechaEmision>25/01/2022</fechaEmision>
        <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>
        <obligadoContabilidad>SI</obligadoContabilidad>
        <tipoIdentificacionProveedor>05</tipoIdentificacionProveedor>
        <razonSocialProveedor>EC Test Partner AàÁ³$£€èêÈÊöÔÇç¡⅛&amp;@™</razonSocialProveedor>
        <identificacionProveedor>0453661050</identificacionProveedor>
        <direccionProveedor>Av. Libertador Simón Bolívar 1155</direccionProveedor>
        <totalSinImpuestos>20.000000</totalSinImpuestos>
        <totalDescuento>0.00</totalDescuento>
        <codDocReembolso>41</codDocReembolso>
        <totalComprobantesReembolso>22.40</totalComprobantesReembolso>
        <totalBaseImponibleReembolso>20.00</totalBaseImponibleReembolso>
        <totalImpuestoReembolso>2.40</totalImpuestoReembolso>
        <totalConImpuestos>
            <totalImpuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>2</codigoPorcentaje>
                <baseImponible>20.000000</baseImponible>
                <valor>2.40</valor>
            </totalImpuesto>
        </totalConImpuestos>
        <importeTotal>22.40</importeTotal>
        <moneda>DOLAR</moneda>
        <pagos>
            <pago>
                <formaPago>16</formaPago>
                <total>6.72</total>
                <plazo>0</plazo>
                <unidadTiempo>dias</unidadTiempo>
            </pago>
            <pago>
                <formaPago>16</formaPago>
                <total>15.68</total>
                <plazo>34</plazo>
                <unidadTiempo>dias</unidadTiempo>
            </pago>
        </pagos>
    </infoLiquidacionCompra>
    <detalles>
        <detalle>
            <codigoPrincipal>N/A</codigoPrincipal>
            <descripcion>product_a</descripcion>
            <cantidad>1.000000</cantidad>
            <precioUnitario>10.000000</precioUnitario>
            <descuento>0.00</descuento>
            <precioTotalSinImpuesto>10.00</precioTotalSinImpuesto>
            <impuestos>
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <tarifa>12.000000</tarifa>
                    <baseImponible>10.000000</baseImponible>
                    <valor>1.20</valor>
                </impuesto>
            </impuestos>
        </detalle>
        <detalle>
            <codigoPrincipal>N/A</codigoPrincipal>
            <descripcion>product_b</descripcion>
            <cantidad>1.000000</cantidad>
            <precioUnitario>10.000000</precioUnitario>
            <descuento>0.00</descuento>
            <precioTotalSinImpuesto>10.00</precioTotalSinImpuesto>
            <impuestos>
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <tarifa>12.000000</tarifa>
                    <baseImponible>10.000000</baseImponible>
                    <valor>1.20</valor>
                </impuesto>
            </impuestos>
        </detalle>
    </detalles>
    <reembolsos>
        <reembolsoDetalle>
            <tipoIdentificacionProveedorReembolso>04</tipoIdentificacionProveedorReembolso>
            <identificacionProveedorReembolso>0453661050152</identificacionProveedorReembolso>
            <codPaisPagoProveedorReembolso>593</codPaisPagoProveedorReembolso>
            <tipoProveedorReembolso>01</tipoProveedorReembolso>
            <codDocReembolso>01</codDocReembolso>
            <estabDocReembolso>001</estabDocReembolso>
            <ptoEmiDocReembolso>001</ptoEmiDocReembolso>
            <secuencialDocReembolso>000000156</secuencialDocReembolso>
            <fechaEmisionDocReembolso>25/01/2022</fechaEmisionDocReembolso>
            <numeroautorizacionDocReemb>1234567890</numeroautorizacionDocReemb>
            <detalleImpuestos>
                <detalleImpuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>2</codigoPorcentaje>
                <tarifa>12</tarifa>
                <baseImponibleReembolso>20.00</baseImponibleReembolso>
                <impuestoReembolso>2.40</impuestoReembolso>
                </detalleImpuesto>
            </detalleImpuestos>
        </reembolsoDetalle>
    </reembolsos>
    <infoAdicional>
        <campoAdicional nombre="Referencia">LiqCo 001-001-000000001</campoAdicional>
    </infoAdicional>
</liquidacionCompra>
"""

L10N_EC_EDI_REIMBURSEMENT_LIQUIDATION_WTH_XPATH = """
<xpath expr="//pagoLocExt" position="after">
    <totalComprobantesReembolso>21.20</totalComprobantesReembolso>
    <totalBaseImponibleReembolso>20.00</totalBaseImponibleReembolso>
    <totalImpuestoReembolso>1.20</totalImpuestoReembolso>
</xpath>
<xpath expr="//docsSustento" position="replace">
    <docsSustento>
        <docSustento>
            <codSustento>01</codSustento>
            <codDocSustento>41</codDocSustento>
            <numDocSustento>001001000000001</numDocSustento>
            <fechaEmisionDocSustento>25/01/2022</fechaEmisionDocSustento>
            <pagoLocExt>01</pagoLocExt>
            <totalComprobantesReembolso>22.40</totalComprobantesReembolso>
            <totalBaseImponibleReembolso>20.00</totalBaseImponibleReembolso>
            <totalImpuestoReembolso>2.40</totalImpuestoReembolso>
            <totalSinImpuestos>20.00</totalSinImpuestos>
            <importeTotal>22.40</importeTotal>
            <impuestosDocSustento>
                <impuestoDocSustento>
                    <codImpuestoDocSustento>2</codImpuestoDocSustento>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <baseImponible>20.00</baseImponible>
                    <tarifa>12.00</tarifa>
                    <valorImpuesto>2.40</valorImpuesto>
                </impuestoDocSustento>
            </impuestosDocSustento>
            <retenciones>
                <retencion>
                    <codigo>2</codigo>
                    <codigoRetencion>3</codigoRetencion>
                    <baseImponible>20.00</baseImponible>
                    <porcentajeRetener>100.00</porcentajeRetener>
                    <valorRetenido>20.00</valorRetenido>
                </retencion>
            </retenciones>
            <reembolsos>
            <reembolsoDetalle>
                <tipoIdentificacionProveedorReembolso>04</tipoIdentificacionProveedorReembolso>
                <identificacionProveedorReembolso>0453661050152</identificacionProveedorReembolso>
                <codPaisPagoProveedorReembolso>593</codPaisPagoProveedorReembolso>
                <tipoProveedorReembolso>01</tipoProveedorReembolso>
                <codDocReembolso>01</codDocReembolso>
                <estabDocReembolso>001</estabDocReembolso>
                <ptoEmiDocReembolso>001</ptoEmiDocReembolso>
                <secuencialDocReembolso>000000156</secuencialDocReembolso>
                <fechaEmisionDocReembolso>25/01/2022</fechaEmisionDocReembolso>
                <numeroAutorizacionDocReemb>1234567890</numeroAutorizacionDocReemb>
                <detalleImpuestos>
                    <detalleImpuesto>
                        <codigo>2</codigo>
                        <codigoPorcentaje>2</codigoPorcentaje>
                        <tarifa>12</tarifa>
                        <baseImponibleReembolso>20.00</baseImponibleReembolso>
                        <impuestoReembolso>2.40</impuestoReembolso>
                    </detalleImpuesto>
                </detalleImpuestos>
            </reembolsoDetalle>
            </reembolsos>
            <pagos>
                <pago>
                    <formaPago>16</formaPago>
                    <total>22.40</total>
                </pago>
            </pagos>
        </docSustento>
    </docsSustento>
</xpath>
"""
