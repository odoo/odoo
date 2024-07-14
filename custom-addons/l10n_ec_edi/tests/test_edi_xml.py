# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from lxml import etree
from odoo import Command
from odoo.tests import tagged

from .common import (L10N_EC_EDI_XML_CREDIT_NOTE, L10N_EC_EDI_XML_DEBIT_NOTE,
                     L10N_EC_EDI_XML_IN_WTH, L10N_EC_EDI_XML_OUT_INV,
                     L10N_EC_EDI_XML_PURCHASE_LIQ,
                     L10N_EC_EDI_XML_PURCHASE_LIQ_WTH,
                     L10N_EC_EDI_XPATH_INVOICE_IN,
                     L10N_EC_EDI_XPATH_INVOICE_IN_CUSTOM_TAXPAYER,
                     TestEcEdiCommon)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEcEdiXmls(TestEcEdiCommon):

    # ===== CUSTOMER INVOICES =====

    def test_xml_tree_out_invoice_basic(self, invoice_line_args=None, xpath=None):
        out_invoice = self.get_invoice({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
        }, invoice_line_args=invoice_line_args)
        self.assert_xml_tree_equal(out_invoice, L10N_EC_EDI_XML_OUT_INV, xpath=xpath)

    def test_xml_tree_out_05_invoice_basic(self):
        line_vals = self.get_invoice_line_vals(vat_tax_xmlid='tax_vat_05_510_sup_01')
        self.test_xml_tree_out_invoice_basic(invoice_line_args=line_vals, xpath="""
            <xpath expr="//totalConImpuestos/totalImpuesto" position="replace">
                <totalImpuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>5</codigoPorcentaje>
                    <baseImponible>400.000000</baseImponible>
                    <tarifa>5.000000</tarifa>
                    <valor>20.00</valor>
                </totalImpuesto>
            </xpath>
            <xpath expr="//importeTotal" position="replace">
                <importeTotal>420.00</importeTotal>
            </xpath>
            <xpath expr="//pago/total" position="replace">
                <total>420.00</total>
            </xpath>
            <xpath expr="//detalle/impuestos/impuesto" position="replace">
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>5</codigoPorcentaje>
                    <tarifa>5.000000</tarifa>
                    <baseImponible>400.000000</baseImponible>
                    <valor>20.00</valor>
                </impuesto>
            </xpath>
        """)

    def test_xml_tree_out_15_invoice_basic(self):
        line_vals = self.get_invoice_line_vals(vat_tax_xmlid='tax_vat_15_510_sup_01')
        self.test_xml_tree_out_invoice_basic(
            invoice_line_args=line_vals,
            xpath="""
            <xpath expr="//totalConImpuestos/totalImpuesto" position="replace">
                <totalImpuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>4</codigoPorcentaje>
                    <baseImponible>400.000000</baseImponible>
                    <tarifa>15.000000</tarifa>
                    <valor>60.00</valor>
                </totalImpuesto>
            </xpath>
            <xpath expr="//importeTotal" position="replace">
                <importeTotal>460.00</importeTotal>
            </xpath>
            <xpath expr="//pago/total" position="replace">
                <total>460.00</total>
            </xpath>
            <xpath expr="//detalle/impuestos/impuesto" position="replace">
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>4</codigoPorcentaje>
                    <tarifa>15.000000</tarifa>
                    <baseImponible>400.000000</baseImponible>
                    <valor>60.00</valor>
                </impuesto>
            </xpath>
        """)

    def test_xml_tree_out_invoice_tax_included(self):
        """Checks the XML of the basic invoice when a tax is modified to be included in price."""
        self._get_tax_by_xml_id('tax_vat_510_sup_01').price_include = True
        self.test_xml_tree_out_invoice_basic(xpath="""
            <xpath expr="//totalSinImpuestos" position="replace">
                <totalSinImpuestos>357.140000</totalSinImpuestos>
            </xpath>
            <xpath expr="//totalDescuento" position="replace">
                <totalDescuento>89.29</totalDescuento>
            </xpath>
            <xpath expr="//totalImpuesto/baseImponible" position="replace">
                <baseImponible>357.140000</baseImponible>
            </xpath>
            <xpath expr="//totalImpuesto/valor" position="replace">
                <valor>42.86</valor>
            </xpath>
            <xpath expr="//importeTotal" position="replace">
                <importeTotal>400.00</importeTotal>
            </xpath>
            <xpath expr="//pago/total" position="replace">
                <total>400.00</total>
            </xpath>
            <xpath expr="//detalle" position="replace">
                <detalle>
                    <codigoPrincipal>N/A</codigoPrincipal>
                    <descripcion>product_a</descripcion>
                    <cantidad>5.000000</cantidad>
                    <precioUnitario>89.285000</precioUnitario>
                    <descuento>89.29</descuento>
                    <precioTotalSinImpuesto>357.14</precioTotalSinImpuesto>
                    <impuestos>
                        <impuesto>
                            <codigo>2</codigo>
                            <codigoPorcentaje>2</codigoPorcentaje>
                            <tarifa>12.000000</tarifa>
                            <baseImponible>357.140000</baseImponible>
                            <valor>42.86</valor>
                        </impuesto>
                    </impuestos>
                </detalle>
            </xpath>
        """)

    def test_xml_tree_out_invoice_richer(self, xpath=""):
        """Checks the XML of an invoice with
        - 2 lines with the same product, but different taxes (one is tax included in price)
        - non-integer quantities
        - discounts
        """
        line_vals = self.get_invoice_line_vals()
        line_vals.extend([Command.create({
            'product_id': self.product_b.id,
            'price_unit': 1.23,
            'quantity': 12.12,
            'tax_ids': [Command.set(self._get_tax_by_xml_id('tax_vat_444').ids)],
        }), Command.create({
            'product_id': self.product_b.id,
            'price_unit': 0.12,
            'quantity': 120,
            'discount': 21,
            'tax_ids': [Command.set(self._get_tax_by_xml_id('tax_vat_412').ids)],
        })])
        self._get_tax_by_xml_id('tax_vat_412').amount_type = 'division'  # tax included in price
        self.test_xml_tree_out_invoice_basic(invoice_line_args=line_vals, xpath="""
            <xpath expr="//totalSinImpuestos" position="replace">
                <totalSinImpuestos>426.290000</totalSinImpuestos>
            </xpath>
            <xpath expr="//totalDescuento" position="replace">
                <totalDescuento>103.03</totalDescuento>
            </xpath>
            <xpath expr="//totalImpuesto/baseImponible" position="replace">
                <baseImponible>426.290000</baseImponible>
            </xpath>
            <xpath expr="//totalImpuesto/valor" position="replace">
                <valor>51.34</valor>
            </xpath>
            <xpath expr="//importeTotal" position="replace">
                <importeTotal>477.63</importeTotal>
            </xpath>
            <xpath expr="//pagos/pago" position="replace">
                <pago>
                    <formaPago>16</formaPago>
                    <total>477.63</total>
                </pago>
            </xpath>
            <xpath expr="//detalles/detalle" position="after">
                <detalle>
                    <codigoPrincipal>N/A</codigoPrincipal>
                    <descripcion>product_b</descripcion>
                    <cantidad>12.120000</cantidad>
                    <precioUnitario>1.230198</precioUnitario>
                    <descuento>0.00</descuento>
                    <precioTotalSinImpuesto>14.91</precioTotalSinImpuesto>
                    <impuestos>
                        <impuesto>
                            <codigo>2</codigo>
                            <codigoPorcentaje>2</codigoPorcentaje>
                            <tarifa>12.000000</tarifa>
                            <baseImponible>14.910000</baseImponible>
                            <valor>1.79</valor>
                        </impuesto>
                    </impuestos>
                </detalle>
                <detalle>
                    <codigoPrincipal>N/A</codigoPrincipal>
                    <descripcion>product_b</descripcion>
                    <cantidad>120.000000</cantidad>
                    <precioUnitario>0.120042</precioUnitario>
                    <descuento>3.03</descuento>
                    <precioTotalSinImpuesto>11.38</precioTotalSinImpuesto>
                    <impuestos>
                        <impuesto>
                            <codigo>2</codigo>
                            <codigoPorcentaje>2</codigoPorcentaje>
                            <tarifa>12.000000</tarifa>
                            <baseImponible>11.380000</baseImponible>
                            <valor>1.55</valor>
                        </impuesto>
                    </impuestos>
                </detalle>
            </xpath>
        """ if not xpath else xpath)

    def test_xml_tree_out_invoice_multicurrency(self):
        """Checks the XML of the 'richer' invoice when created in another currency than USD.
        In EC, USD is the official currency and the govt expects it to be used in XMLs."""
        currency_euro = self.env.ref('base.EUR')
        currency_euro.active = True
        self.env['res.currency.rate'].create({
            'name': self.frozen_today,
            'company_rate': 0.5,
            'currency_id': currency_euro.id,
            'company_id': self.env.company.id,
        })

        for journal in (self.company_data['default_journal_sale'], self.company_data['default_journal_purchase']):
            journal.currency_id = currency_euro.id

        self.test_xml_tree_out_invoice_richer(xpath="""
            <xpath expr="//totalSinImpuestos" position="replace">
                <totalSinImpuestos>852.580000</totalSinImpuestos>
            </xpath>
            <xpath expr="//totalDescuento" position="replace">
                <totalDescuento>206.06</totalDescuento>
            </xpath>
            <xpath expr="//totalImpuesto/baseImponible" position="replace">
                <baseImponible>852.580000</baseImponible>
            </xpath>
            <xpath expr="//totalImpuesto/valor" position="replace">
                <valor>102.68</valor>
            </xpath>
            <xpath expr="//importeTotal" position="replace">
                <importeTotal>955.26</importeTotal>
            </xpath>
            <xpath expr="//pagos/pago" position="replace">
                <pago>
                    <formaPago>16</formaPago>
                    <total>955.26</total>
                </pago>
            </xpath>
            <xpath expr="//detalles/detalle" position="replace">
                <detalle>
                    <codigoPrincipal>N/A</codigoPrincipal>
                    <descripcion>product_a</descripcion>
                    <cantidad>5.000000</cantidad>
                    <precioUnitario>200.000000</precioUnitario>
                    <descuento>200.00</descuento>
                    <precioTotalSinImpuesto>800.00</precioTotalSinImpuesto>
                    <impuestos>
                        <impuesto>
                            <codigo>2</codigo>
                            <codigoPorcentaje>2</codigoPorcentaje>
                            <tarifa>12.000000</tarifa>
                            <baseImponible>800.000000</baseImponible>
                            <valor>96.00</valor>
                        </impuesto>
                    </impuestos>
                    </detalle>
                <detalle>
                    <codigoPrincipal>N/A</codigoPrincipal>
                    <descripcion>product_b</descripcion>
                    <cantidad>12.120000</cantidad>
                    <precioUnitario>2.460396</precioUnitario>
                    <descuento>0.00</descuento>
                    <precioTotalSinImpuesto>29.82</precioTotalSinImpuesto>
                    <impuestos>
                        <impuesto>
                            <codigo>2</codigo>
                            <codigoPorcentaje>2</codigoPorcentaje>
                            <tarifa>12.000000</tarifa>
                            <baseImponible>29.820000</baseImponible>
                            <valor>3.58</valor>
                        </impuesto>
                    </impuestos>
                </detalle>
                <detalle>
                    <codigoPrincipal>N/A</codigoPrincipal>
                    <descripcion>product_b</descripcion>
                    <cantidad>120.000000</cantidad>
                    <precioUnitario>0.240084</precioUnitario>
                    <descuento>6.06</descuento>
                    <precioTotalSinImpuesto>22.76</precioTotalSinImpuesto>
                    <impuestos>
                        <impuesto>
                            <codigo>2</codigo>
                            <codigoPorcentaje>2</codigoPorcentaje>
                            <tarifa>12.000000</tarifa>
                            <baseImponible>22.760000</baseImponible>
                            <valor>3.10</valor>
                        </impuesto>
                    </impuestos>
                </detalle>
            </xpath>
        """)

    # ===== DEBIT & CREDIT NOTES, LIQUIDATIONS =====

    def test_xml_tree_debit_note(self):
        invoice = self.get_invoice({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
        })
        invoice.action_post()
        debit_note_wizard = self.env['account.debit.note'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'date': self.frozen_today,
            'reason': 'no reason',
            'copy_lines': True,
        })
        with freeze_time(self.frozen_today):
            debit_note_wizard.create_debit()
            debit_note = self.env['account.move'].search([('debit_origin_id', '=', invoice.id)])
            debit_note.ensure_one()
        self.assert_xml_tree_equal(debit_note, L10N_EC_EDI_XML_DEBIT_NOTE)

    def test_xml_tree_credit_note(self):
        invoice = self.get_invoice({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
        })
        invoice.action_post()
        credit_note_wizard = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'date': self.frozen_today,
            'journal_id': invoice.journal_id.id,
            'reason': 'no reason',
        })
        with freeze_time(self.frozen_today):
            credit_note_wizard.modify_moves()
            credit_note = self.env['account.move'].search([('reversed_entry_id', '=', invoice.id)])
            credit_note.ensure_one()
        self.assert_xml_tree_equal(credit_note, L10N_EC_EDI_XML_CREDIT_NOTE, post_move=False)

    def test_xml_tree_purchase_liquidation(self):
        self.partner_b.country_id = self.env.ref('base.us').id
        journal_liq = self.env['account.journal'].search([
            ('company_id', '=', self.company_data['company'].id),
            ('code', '=', 'LIQCO')
        ])
        in_invoice = self.get_invoice({
            'move_type': 'in_invoice',
            'partner_id': self.partner_b.id,
            'journal_id': journal_liq.id,
        })
        self.assert_xml_tree_equal(in_invoice, L10N_EC_EDI_XML_PURCHASE_LIQ)

    # ===== WITHHOLDS =====

    def test_purchase_liquidation_wth(self):
        """Checks the XML of a withhold on top of a purchase liquidation that has two different
        tax supports and a domestic supplier with identification type "cedula"."""
        def create_wth_lines(wizard, invoice):
            # Create withhold lines manually
            self.env['l10n_ec.wizard.account.withhold.line'].create({
                'invoice_id': invoice.id,
                'wizard_id': wizard.id,
                'base': 12,
                'tax_id': self._get_tax_by_xml_id('tax_withhold_vat_100').ids[0],
                'taxsupport_code': '01',
                'amount': 12,
            })
            self.env['l10n_ec.wizard.account.withhold.line'].create({
                'invoice_id': invoice.id,
                'wizard_id': wizard.id,
                'base': 23.99,
                'tax_id': self._get_tax_by_xml_id('tax_withhold_vat_100').ids[0],
                'taxsupport_code': '04',
                'amount': 23.99,
            })

        with freeze_time(self.frozen_today):
            purchase_liq = self.get_purchase_liq()
            purchase_liq.action_post()
            withhold = self.get_withhold(purchase_liq, create_wth_lines)
            self.assert_xml_tree_equal(withhold, L10N_EC_EDI_XML_PURCHASE_LIQ_WTH, post_move=False)

    def test_xml_tree_in_withhold_foreign_partner_dm(self):
        """Checks the XML of a purchase withhold whose invoice originates from a foreign partner."""
        self.partner_b.country_id = self.env.ref('base.dm').id
        self.partner_b.l10n_latam_identification_type_id = self.env.ref('l10n_latam_base.it_vat')

        def create_wth_lines(wizard, invoice):
            self.env['l10n_ec.wizard.account.withhold.line'].create({
                'invoice_id': invoice.id,
                'wizard_id': wizard.id,
                'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_502_422').ids[0],
                'taxsupport_code': '02',
                'base': 400,
                'amount': 88,  # VAT, 22.00% of 400
            })
            wizard.foreign_regime = '01'
        xpath = self.get_withhold_xpath_for_taxes(tax_percent='22.00', withhold_amount='88.00', tax_code=502)
        xpath += """
            <xpath expr="//tipoIdentificacionSujetoRetenido" position="replace">
                <tipoIdentificacionSujetoRetenido>08</tipoIdentificacionSujetoRetenido>
                <tipoSujetoRetenido>01</tipoSujetoRetenido>
            </xpath>
            <xpath expr="//identificacionSujetoRetenido" position="replace">
                <identificacionSujetoRetenido>0453661050</identificacionSujetoRetenido>
            </xpath>
            <xpath expr="//codSustento" position="replace">
                <codSustento>02</codSustento>
            </xpath>
            <xpath expr="//codDocSustento" position="replace">
                <codDocSustento>09</codDocSustento>
            </xpath>
            <xpath expr="//pagoLocExt" position="replace">
                <pagoLocExt>02</pagoLocExt>
                <tipoRegi>01</tipoRegi>
                <paisEfecPago>136</paisEfecPago>
                <aplicConvDobTrib>NO</aplicConvDobTrib>
                <pagExtSujRetNorLeg>SI</pagExtSujRetNorLeg>
                <pagoRegFis>SI</pagoRegFis>
            </xpath>
            <xpath expr="//importeTotal" position="replace">
                <importeTotal>400.00</importeTotal>
            </xpath>
            <xpath expr="//impuestosDocSustento/impuestoDocSustento" position="replace">
                <impuestoDocSustento>
                    <codImpuestoDocSustento>2</codImpuestoDocSustento>
                    <codigoPorcentaje>0</codigoPorcentaje>
                    <baseImponible>400.00</baseImponible>
                    <tarifa>0.00</tarifa>
                    <valorImpuesto>0.00</valorImpuesto>
                </impuestoDocSustento>
            </xpath>
            <xpath expr="//pagos/pago" position="replace">
                <pago>
                    <formaPago>01</formaPago>
                    <total>400.00</total>
                </pago>
            </xpath>
        """
        invoice_args = {'partner_id': self.partner_b.id}
        invoice_line_args = [Command.create({
            'product_id': self.product_a.id,
            'price_unit': 100.0,
            'quantity': 5,
            'discount': 20,
            'tax_ids': [Command.set(self._get_tax_by_xml_id('tax_vat_518_sup_02').ids)],
        })]
        self.get_and_test_xml_tree_in_withhold(line_creation_method=create_wth_lines, xpath=xpath,
                                               invoice_args=invoice_args, invoice_line_args=invoice_line_args)

    def test_xml_tree_in_withhold_suggested_tax_credit_card(self):
        """Checks the XML of a purchase withhold whose invoice's payment method is a credit card.
        Payments with credit/debit/gift cards: tax must be company.l10n_ec_withhold_credit_card_tax_id."""
        self.get_and_test_xml_tree_in_withhold(
            invoice_args={
                'l10n_ec_sri_payment_id': self.env['l10n_ec.sri.payment'].search([('code', '=', 16)], limit=1).id
            },
            xpath=self.get_withhold_xpath_for_taxes(tax_percent='0.00', tax_code='332G', withhold_amount='0.00', payment_code=16)
        )

    def test_xml_tree_in_withhold_suggested_tax_fallback_goods(self):
        """Checks the XML of a purchase withhold for goods.
        Fallback tax for goods: company.l10n_ec_withhold_goods_tax_id."""
        self.get_and_test_xml_tree_in_withhold()

    def test_xml_tree_in_withhold_suggested_tax_fallback_services(self):
        """Checks the XML of a purchase withhold for goods.
        Fallback tax for services: company.l10n_ec_withhold_services_tax_id."""
        self.product_a.type = 'service'
        self.get_and_test_xml_tree_in_withhold(
            xpath=self.get_withhold_xpath_for_taxes(tax_percent='2.75', withhold_amount='11.00', tax_code=3440)
        )

    def test_xml_tree_in_withhold_suggested_tax_taxpayer_type(self):
        """Checks the XML of a purchase withhold for RIMPE partner.
        Tax for partner with taxpayer type: partner.l10n_ec_taxpayer_type_id.profit_withhold_tax_id."""
        self.partner_a.l10n_ec_taxpayer_type_id = self.env.ref('l10n_ec_edi.l10n_ec_taxpayer_type_13')
        self.get_and_test_xml_tree_in_withhold(
            xpath=self.get_withhold_xpath_for_taxes(tax_percent='1.00', withhold_amount='4.00', tax_code=343))

    def test_xml_custom_taxpayer_type_partner_on_purchase_invoice_withhold(self):
        """Checks the XML of a purchase withhold for a partner with a custom taxpayer type"""
        self.set_custom_taxpayer_type_on_partner_a()
        self.test_xml_withholding_purchase_invoice(custom_xpath=L10N_EC_EDI_XPATH_INVOICE_IN_CUSTOM_TAXPAYER)

    def test_xml_tree_in_withhold_manual_taxes(self):
        """Checks the XML of a purchase withhold where lines have been created manually.
        Lines are created with different taxes (one VAT and one profit) and tax supports."""
        line_vals_1 = self.get_invoice_line_vals()
        line_vals_2 = self.get_invoice_line_vals()
        line_vals_2[0][2]['tax_ids'] = [Command.set(self._get_tax_by_xml_id('tax_vat_512_sup_07').ids)]
        line_vals_3 = self.get_invoice_line_vals()
        line_vals_3[0][2]['tax_ids'] = [Command.set(self._get_tax_by_xml_id('tax_vat_510_sup_01').ids)]

        def create_wth_lines(wizard, invoice):
            wizard_line_cls = self.env['l10n_ec.wizard.account.withhold.line']
            # base is chosen so it is accepted for both VAT and profit lines
            common_vals = {'invoice_id': invoice.id, 'wizard_id': wizard.id, 'base': 42}
            wizard_line_cls.create({
                **common_vals,
                'tax_id': self._get_tax_by_xml_id('tax_withhold_vat_10').ids[0],
                'taxsupport_code': '01',
                'amount': 4.2,  # VAT, 10% of 42
            })
            wizard_line_cls.create({
                **common_vals,
                'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_304D').ids[0],
                'taxsupport_code': '07',
                'amount': 3.36,  # profit, 8% of 42
            })
        self.get_and_test_xml_tree_in_withhold(
            line_creation_method=create_wth_lines,
            invoice_line_args=line_vals_1 + line_vals_2 + line_vals_3,
            xpath="""
            <xpath expr="//docsSustento" position="replace">
                <docsSustento>
                    <docSustento>
                    <codSustento>01</codSustento>
                    <codDocSustento>01</codDocSustento>
                    <numDocSustento>001001000000001</numDocSustento>
                    <fechaEmisionDocSustento>25/01/2022</fechaEmisionDocSustento>
                    <pagoLocExt>01</pagoLocExt>
                    <totalSinImpuestos>800.00</totalSinImpuestos>
                    <importeTotal>896.00</importeTotal>
                    <impuestosDocSustento>
                        <impuestoDocSustento>
                            <codImpuestoDocSustento>2</codImpuestoDocSustento>
                            <codigoPorcentaje>2</codigoPorcentaje>
                            <baseImponible>800.00</baseImponible>
                            <tarifa>12.00</tarifa>
                            <valorImpuesto>96.00</valorImpuesto>
                        </impuestoDocSustento>
                    </impuestosDocSustento>
                    <retenciones>
                        <retencion>
                            <codigo>2</codigo>
                            <codigoRetencion>9</codigoRetencion>
                            <baseImponible>42.00</baseImponible>
                            <porcentajeRetener>10.00</porcentajeRetener>
                            <valorRetenido>4.20</valorRetenido>
                        </retencion>
                    </retenciones>
                    <pagos>
                        <pago>
                            <formaPago>01</formaPago>
                            <total>896.00</total>
                        </pago>
                    </pagos>
                </docSustento>
                    <docSustento>
                        <codSustento>07</codSustento>
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
                                <codigoRetencion>304D</codigoRetencion>
                                <baseImponible>42.00</baseImponible>
                                <porcentajeRetener>8.00</porcentajeRetener>
                                <valorRetenido>3.36</valorRetenido>
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
            </xpath>
            """)

    def test_xml_withholding_purchase_invoice(self, custom_xpath=False):
        # test the prebuild xml withhold for purchase invoice
        wizard, _purchase_invoice = self.get_wizard_and_purchase_invoice()
        with freeze_time(self.frozen_today):
            withhold = wizard.action_create_and_post_withhold()
        xpath = """
            <xpath expr="//tipoIdentificacionSujetoRetenido" position="replace">
                <tipoIdentificacionSujetoRetenido>04</tipoIdentificacionSujetoRetenido>
            </xpath>
            <xpath expr="//identificacionSujetoRetenido" position="replace">
                <identificacionSujetoRetenido>0453661050152</identificacionSujetoRetenido>
            </xpath>
            <xpath expr="//claveAcceso" position="replace">
                <claveAcceso>2501202207179236683600110010010000000013121521419</claveAcceso>
            </xpath>
        """
        xpath += L10N_EC_EDI_XPATH_INVOICE_IN
        if custom_xpath:
            xpath += custom_xpath
        self.assert_xml_tree_equal(withhold, L10N_EC_EDI_XML_IN_WTH, post_move=False, xpath=xpath)

    # ===== HELPERS =====

    def get_purchase_liq(self):
        """Creates a purchase liquidation with two lines with different tax supports."""
        def get_purchase_liq_line_vals():
            return [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'quantity': 1,
                'discount': 0,
                'tax_ids': [Command.set(self._get_tax_by_xml_id('tax_vat_510_sup_01').ids)],
            }), Command.create({
                'product_id': self.product_b.id,
                'price_unit': 100.0,
                'quantity': 2,
                'discount': 0,
                'tax_ids': [Command.set(self._get_tax_by_xml_id('tax_vat_512_sup_04').ids)],
            })]

        journal_liq = self.env['account.journal'].search([
            ('company_id', '=', self.company_data['company'].id),
            ('code', '=', 'LIQCO')
        ], limit=1)
        purchase_liquidation = self.get_invoice({
            'move_type': 'in_invoice',
            'partner_id': self.partner_b.id,
            'journal_id': journal_liq.id,
            'invoice_line_ids': get_purchase_liq_line_vals()
        })
        return purchase_liquidation

    def get_withhold(self, invoice, line_creation_method=None):
        """Creates a withhold on the provided invoice, with an option to create the lines 'manually'."""
        # Create wizard
        with freeze_time(self.frozen_today):
            wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=invoice.id, active_model='account.move')
            wizard = wizard.create({})
        wizard.document_number = '001-001-000000001'

        # Add withhold lines
        if line_creation_method:
            for line in wizard.withhold_line_ids:
                line.unlink()
            line_creation_method(wizard, invoice)

        # Create withhold
        withhold = wizard.action_create_and_post_withhold()
        return withhold

    def get_withhold_xpath_for_taxes(self, tax_percent, tax_code, withhold_amount, payment_code='01'):
        """Provides an xpath modifying a withhold XML in accordance with the provided taxes."""
        return f"""
            <xpath expr="//retencion" position="replace">
                <retencion>
                    <codigo>1</codigo>
                    <codigoRetencion>{tax_code}</codigoRetencion>
                    <baseImponible>400.00</baseImponible>
                    <porcentajeRetener>{tax_percent}</porcentajeRetener>
                    <valorRetenido>{withhold_amount}</valorRetenido>
                </retencion>
            </xpath>
            <xpath expr="//pago" position="replace">
                <pago>
                    <formaPago>{payment_code}</formaPago>
                    <total>448.00</total>
                </pago>
            </xpath>
        """

    def get_and_test_xml_tree_in_withhold(self, line_creation_method=None, invoice_args=None, invoice_line_args=None, xpath=None):
        """Generic method for creating an invoice, adding a related withhold, and checking its generated XML."""
        # Create the invoice and withhold
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'l10n_ec_sri_payment_id': self.env['l10n_ec.sri.payment'].search([('code', '=', '01')], limit=1).id
        }
        if invoice_args:
            invoice_vals.update(invoice_args)
        in_invoice = self.get_invoice(invoice_vals, invoice_line_args)
        in_invoice._post()
        residual_before = in_invoice.amount_residual
        in_wth = self.get_withhold(in_invoice, line_creation_method)

        # Check the generated XML document
        self.assert_xml_tree_equal(in_wth, L10N_EC_EDI_XML_IN_WTH, post_move=False, xpath=xpath)

        # Check the line reconciliation (posting withhold decreases the invoice's residual amount)
        residual_expected = residual_before - sum([line.l10n_ec_withhold_tax_amount for line in in_wth.l10n_ec_withhold_line_ids])
        self.assertEqual(residual_expected, in_invoice.amount_residual)

    def assert_xml_tree_equal(self, move, xml_string, post_move=True, xpath=None):
        with freeze_time(self.frozen_today):
            post_move and move.action_post()
            move_string, errors = self.env['account.edi.format'].with_context(skip_xsd=True)._l10n_ec_generate_xml(move)
            self.assertFalse(errors)
            move_xml = etree.fromstring(move_string.encode())
            xml_expected = etree.fromstring(xml_string)
            if xpath:
                xml_expected = self.with_applied_xpath(xml_expected, xpath)
            self.assertXmlTreeEqual(move_xml, xml_expected)
