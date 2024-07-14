# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged
from odoo import Command
from pytz import timezone
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEcEdiCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ec', edi_format_ref='l10n_ec_edi.ecuadorian_edi_format'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

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

        cls.env['account.chart.template']._l10n_ec_configure_ecuadorian_journals(cls.env.company)

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
            'detailed_type': 'service',
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
                    <porcentajeRetener>1.75</porcentajeRetener>
                    <valorRetenido>7.00</valorRetenido>
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
                <porcentajeRetener>1.75</porcentajeRetener>
                <valorRetenido>7.00</valorRetenido>
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
                <porcentajeRetener>1.75</porcentajeRetener>
                <valorRetenido>8.75</valorRetenido>
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
