<<<<<<< HEAD
||||||| MERGE BASE
=======
from lxml import etree

from odoo import Command
from odoo.tests import tagged
from odoo.exceptions import UserError
from odoo.addons.l10n_it_edi.tests.test_edi_export import TestItEdiExport


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiNddExport(TestItEdiExport):

    def _force_simplified(self, partner, price_unit=100.00):
        td07 = self.env['l10n_it.document.type'].search([('code', '=', 'TD07')], limit=1)
        return self.env['account.move'].with_company(self.company).create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': partner.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'cheap_line',
                    'price_unit': price_unit,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
            'l10n_it_document_type': td07.id,
        })

    def _get_simplified_errors(self, moves):
        return [
            k
            for k, v in moves._l10n_it_edi_is_simplified_checks().items()
            if v.get('level') != 'info'
        ]

    def _get_partner_simplified_errors(self, invoice):
        return list(invoice.commercial_partner_id._l10n_it_edi_export_check(['partner_simplified']))

    def test_invoice_non_domestic_force_simplified(self):
        """ If the user forces a simplified document type (i.e. TD07) on a non-italian partner, an error is raised """
        invoice = self._force_simplified(self.american_partner)
        self.assertEqual(['l10n_it_edi_partner_simplified'], self._get_partner_simplified_errors(invoice))

    def test_invoice_domestic_force_simplified(self):
        """ If the user forces a simplified document type (i.e. TD07) on an italian partner, it works """
        invoice = self._force_simplified(self.italian_partner_a)
        self.assertEqual([], self._get_simplified_errors(invoice))

    def test_invoice_pa_force_simplified(self):
        """ If the user forces a simplified document type (i.e. TD07) on an italian PA partner, errors are raised """
        invoice = self._force_simplified(self.italian_partner_b)
        self.assertEqual(['l10n_it_edi_partner_simplified'], self._get_partner_simplified_errors(invoice))

    def test_invoice_pa_force_simplified_partner_fails_checks(self):
        """ TD07 forced on a PA partner with a complete address must be blocked """
        invoice = self._force_simplified(self.italian_partner_b)
        invoice.action_post()
        self.assertIn('l10n_it_edi_partner_simplified', invoice._l10n_it_edi_export_data_check())

    def test_forced_simplified_uses_simplified_template(self):
        """ Test that Template and FormatoTrasmissione are both simplified """
        invoice = self._force_simplified(self.italian_partner_a)
        invoice.action_post()
        tree = etree.fromstring(invoice._l10n_it_edi_render_xml())

        self.assertEqual(etree.QName(tree).localname, 'FatturaElettronicaSemplificata')
        self.assertEqual(tree.findtext('.//FormatoTrasmissione'), 'FSM10')
        self.assertEqual(tree.findtext('.//TipoDocumento'), 'TD07')

    def test_forced_simplified_price_over_threshold(self):
        """ If the user forces a simplified document type (i.e. TD07) on a price over the threshold (400€), errors are raised """
        invoice = self._force_simplified(self.italian_partner_a, price_unit=500.00)
        self.assertEqual(['l10n_it_edi_move_simplified_amount'], self._get_simplified_errors(invoice))

    def test_td01_under_threshold_complete_address_exported_as_td01(self):
        """ TD01 under 400€ to a domestic partner with a complete address gets exported as an ordinary invoice """
        invoice = self._force_simplified(self.italian_partner_a)
        invoice.l10n_it_document_type = self.env.ref('l10n_it_edi_ndd.l10n_it_document_type_01')
        invoice.action_post()
        tree = etree.fromstring(invoice._l10n_it_edi_render_xml())

        self.assertEqual(invoice.l10n_it_document_type.code, 'TD01')
        self.assertEqual(etree.QName(tree).localname, 'FatturaElettronica')
        self.assertEqual(tree.findtext('.//FormatoTrasmissione'), 'FPR12')

    def test_td01_price_under_threshold_missing_address_exported_as_td07(self):
        """ TD01 under 400€ to a domestic partner without address gets exported as simplified invoice (TD07) """
        invoice = self._force_simplified(self.italian_partner_no_address_codice)
        invoice.l10n_it_document_type = self.env.ref('l10n_it_edi_ndd.l10n_it_document_type_01')
        invoice.action_post()
        tree = etree.fromstring(invoice._l10n_it_edi_render_xml())

        self.assertEqual(invoice.l10n_it_document_type.code, 'TD07')
        self.assertEqual(etree.QName(tree).localname, 'FatturaElettronicaSemplificata')
        self.assertEqual(tree.findtext('.//FormatoTrasmissione'), 'FSM10')
        self.assertEqual(tree.findtext('.//TipoDocumento'), 'TD07')

    def test_td01_price_over_threshold_exported_as_td01(self):
        """ TD01 over 400€ to a domestic partner gets exported as an ordinary invoice """
        invoice = self._force_simplified(self.italian_partner_a, price_unit=500.00)
        invoice.l10n_it_document_type = self.env.ref('l10n_it_edi_ndd.l10n_it_document_type_01')
        invoice.action_post()
        tree = etree.fromstring(invoice._l10n_it_edi_render_xml())

        self.assertEqual(invoice.l10n_it_document_type.code, 'TD01')
        self.assertEqual(etree.QName(tree).localname, 'FatturaElettronica')
        self.assertEqual(tree.findtext('.//FormatoTrasmissione'), 'FPR12')
        self.assertEqual(tree.findtext('.//TipoDocumento'), 'TD01')

    def test_wizard_alerts_with_only_edi_format(self):
        """ When the Partner has the FatturaPA EDI format set, but nothing is ticked
        on the wizard, the checks raise an error before the XML is generated """
        invoice = self._force_simplified(self.italian_partner_no_VAT_no_codice)
        invoice.action_post()
        wizard = self.env['account.move.send.wizard'].with_context(active_model='account.move', active_ids=invoice.ids).create({})
        self.assertIn('l10n_it_edi_partner_vat_codice_fiscale_missing', wizard.alerts)

    def test_forced_simplified_no_vat_fails_checks(self):
        """ If partner has no VAT and Codice Fiscale the sending must be blocked """
        self.italian_partner_no_VAT_no_codice.invoice_edi_format = 'it_edi_xml'
        invoice = self._force_simplified(self.italian_partner_no_VAT_no_codice)
        invoice.action_post()

        self.assertEqual([], self._get_partner_simplified_errors(invoice))
        self.assertIn('l10n_it_edi_partner_vat_codice_fiscale_missing', invoice._l10n_it_edi_export_data_check())

        with self.assertRaises(UserError):
            self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
        self.assertFalse(invoice.l10n_it_edi_attachment_id)

    def test_wizard_forced_simplified_success(self):
        """ Test the happy path for the wizard, partner has a VAT number, amount is correct, XML is generated """
        invoice = self._force_simplified(self.italian_partner_a)
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'}, extra_edis=set())
        self.assertTrue(invoice.l10n_it_edi_attachment_id)

>>>>>>> FORWARD PORTED
