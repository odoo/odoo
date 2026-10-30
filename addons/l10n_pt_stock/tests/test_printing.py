import re

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_pt_certification.const import PT_CERTIFICATION_NUMBER
from odoo.addons.l10n_pt_stock.tests.common import TestL10nPtStockCommon


def print_versions(html):
    """The print-version labels of ``html``, one per exemplar printed."""
    return re.findall(r'<span id="l10n_pt_print_version">([^<]*)</span>', html)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtStockPrinting(TestL10nPtStockCommon):
    """
    What travels with the goods: the printed transport document and its QR code.

    It can only be printed once issued, signed at validation (Despacho 8632/2014 1.6, 2.1.5), in three
    exemplars, for the recipient, the inspection and the sender (RBC art. 5(2), 6(5)), then as a "2ª
    Via" keeping the original's content (Despacho 8632/2014 2.2.15). It states the places of loading
    and unloading, the start of transport and the recipient with its NIF (RBC art. 4(2), 4(4), 4(9)),
    its number, ATCUD and AT designation, dates as DD-MM-AAAA (Despacho 8632/2014 2.2.4; Portaria
    195/2020). Signatures being deterministic, values are literal.
    """

    # -------------------------------------------------------------------------
    # Printing
    # -------------------------------------------------------------------------

    def _attachments(self, records):
        return self.env['l10n.pt.attachment'].sudo().search([('res_model', '=', records._name), ('res_id', 'in', records.ids)])

    def test_pick_prints_as_in_core(self):
        """A transfer that is no transport document prints without any of its content, at any stage (PT-43)."""
        step = self.make_transfer(self.int_type, partner=False, location_dest=self.shelf_location)
        for picking in (step, self.validate(step)):
            with self.subTest(state=picking.state):
                self.print_pdf_for_real(picking)
                html = self.print_pdf(picking)
                self.assertIn(picking.name, html)
                self.assertNotIn('Local de carga', html)
                self.assertNotIn('ATCUD:', html)
        self.assertNotIssued(step)

    def test_not_issued_refused(self):
        """
        A transport document cannot be printed before it is issued at validation, nor ever when its
        operation type has no series to issue it in; each refusal says what to do (PT-43).
        """
        with self.assertRaisesRegex(UserError, "can only be printed once it is issued"):
            self.print_pdf_for_real(self.make_transfer())
        without_series = self.make_transfer(self.warehouse_2.out_type_id)
        for picking in (without_series, self.validate(without_series)):
            with self.subTest(state=picking.state), self.assertRaisesRegex(UserError, "has no AT series to issue it in"):
                self.print_pdf_for_real(picking)

    def test_unsigned_refused(self):
        """A transport document the signing service could not sign yet cannot be printed (PT-43)."""
        self.signing.available = False
        picking = self.deliver()
        with self.assertRaisesRegex(UserError, "could not be signed yet"):
            self.print_pdf_for_real(picking)
        self.signing.available = True
        self.assertEqual(print_versions(self.print_pdf(picking)), ['Original', 'Duplicado', 'Triplicado'])

    def test_three_exemplars_then_reprint(self):
        """
        The first print of a transport document is made of its Original, Duplicado and Triplicado; the
        next is its 2ª Via, both from the one stored print (PT-39, PT-70).
        """
        picking = self.deliver()
        self.assertEqual(print_versions(self.print_pdf(picking)), ['Original', 'Duplicado', 'Triplicado'])
        self.assertEqual(picking.l10n_pt_print_version, 'original')
        self.assertEqual(print_versions(self.print_pdf(picking)), ['2ª Via'])
        self.assertEqual(picking.l10n_pt_print_version, 'reprint')
        self.assertEqual(len(self._attachments(picking)), 1)

    def test_preview_stores_nothing(self):
        """An HTML render is not a print: nothing stored, the next print is the Original's three exemplars."""
        picking = self.deliver()
        self.assertEqual(print_versions(self.preview(picking)), ['Original'])
        self.assertFalse(picking.l10n_pt_print_version)
        self.assertFalse(self._attachments(picking))
        self.assertEqual(print_versions(self.print_pdf(picking)), ['Original', 'Duplicado', 'Triplicado'])

    def test_reprint_keeps_original_content(self):
        """A reprint serves the content of the original print, even after the customer changed."""
        picking = self.deliver()
        self.assertIn('10 Rua do Ouro', self.print_pdf(picking))
        self.partner_pt.street = '99 Rua Nova'
        reprint = self.print_pdf(picking)
        self.assertIn('10 Rua do Ouro', reprint)
        self.assertNotIn('99 Rua Nova', reprint)

    def test_reprint_reason(self):
        """
        Print on a transport document already printed asks for a reason, logged in the chatter, then
        prints it (Despacho 8632/2014 2.2.16).
        """
        picking = self.deliver()
        self.assertEqual(picking.action_open_reprint_wizard()['type'], 'ir.actions.report')
        self.print_pdf(picking)
        action = picking.action_open_reprint_wizard()
        self.assertEqual(action['res_model'], 'l10n_pt.reprint.reason')
        wizard = self.env['l10n_pt.reprint.reason'].with_context(
            active_model='stock.picking',
            active_ids=picking.ids,
        ).create({'reason': 'Cópia perdida pelo motorista'})
        report_action = wizard.action_log_and_print()
        self.assertEqual(report_action['report_name'], 'stock.report_deliveryslip')
        self.assertIn('Cópia perdida pelo motorista', picking.message_ids[0].body)

    def test_print_transfers_of_two_pt_companies(self):
        """Transport documents of two PT companies print together, each issued in its own company (PT-43)."""
        series_2 = self.series_factory(document_type='outgoing', company_id=self.company_pt_2.id)
        warehouse_2 = self.env['stock.warehouse'].search([('company_id', '=', self.company_pt_2.id)], limit=1)
        warehouse_2.out_type_id.l10n_pt_stock_at_series_id = series_2
        other_company = self.deliver(warehouse_2.out_type_id.with_company(self.company_pt_2))
        pickings = (self.deliver() + other_company).with_context(allowed_company_ids=(self.company_pt + self.company_pt_2).ids)
        html = self.print_pdf(pickings)
        self.assertIn(f'ATCUD:{self.series_gt.at_code}-1', html)
        self.assertIn(f'ATCUD:{series_2.at_code}-1', html)

    # -------------------------------------------------------------------------
    # Content
    # -------------------------------------------------------------------------

    def test_printed_content(self):
        """
        A delivery prints its number and designation, its dates as DD-MM-AAAA in Lisbon time, where the
        goods are loaded and unloaded, when the transport starts, the recipient's NIF, its ATCUD as
        ATCUD:code-n and QR code, and that it is no invoice (PT-39, PT-69, PT-28).
        """
        html = self.print_pdf(self.deliver())
        for expected in (
            'GT 2026/00001',
            'Guia de transporte',
            '15-06-2026 11:00',
            'Local de carga',
            '25 Avenida da Liberdade',
            'Local de descarga',
            '10 Rua do Ouro',
            'Início do transporte',
            'Destinatário:',
            'Cliente PT',
            '- NIF: PT501964843',
            f'ATCUD:{self.series_gt.at_code}-1',
            'barLevel=M',
            'Este documento não serve de fatura',
            f'Processado por programa certificado n.º {PT_CERTIFICATION_NUMBER}/AT',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

    def test_recipient_without_nif(self):
        """A recipient without a NIF is printed as no taxable person, never as 999999990 (RBC art. 4(9); PT-75)."""
        for vat in (False, '999999990'):
            with self.subTest(vat=vat):
                customer = self.env['res.partner'].create({'name': 'Cliente Anónimo', 'vat': vat, 'country_id': self.env.ref('base.pt').id})
                html = self.print_pdf(self.deliver(partner=customer))
                self.assertIn('destinatário não sujeito passivo', html)
                # The QR code itself carries 999999990 (spec v1.1, field B): only the printed text is checked.
                self.assertNotIn('999999990', re.sub(r'src="/report/barcode/[^"]*"', '', html))

    def test_move_between_warehouses_content(self):
        """Between two warehouses, the goods are unloaded at the other warehouse, and the company is the recipient."""
        html = self.print_pdf(self.deliver(self.int_type, partner=False, location_dest=self.warehouse_2.lot_stock_id))
        self.assertIn('50 Rua de Santa Catarina', html)
        self.assertIn(f'{self.company_pt.name}', html)
        self.assertIn('- NIF: PT123456789', html)

    def test_legal_time_zone(self):
        """Dates print in the legal time of the company's region: Azores an hour behind Lisbon and Madeira."""
        picking = self.deliver()
        for state, time_zone in (
            ('base.state_pt_pt-20', 'Atlantic/Azores'),
            ('base.state_pt_pt-30', 'Atlantic/Madeira'),
            ('base.state_pt_pt-11', 'Europe/Lisbon'),
        ):
            with self.subTest(state=state):
                self.company_pt.state_id = self.env.ref(state)
                self.assertEqual(picking._l10n_pt_get_legal_tz(), time_zone)
        self.company_pt.state_id = self.env.ref('base.state_pt_pt-20')
        self.assertIn('15-06-2026 10:00', self.print_pdf(picking))

    # -------------------------------------------------------------------------
    # QR code
    # -------------------------------------------------------------------------

    def test_qr_code(self):
        """
        A transport guide's QR code: the company's and the customer's NIF, the type GT, its date, number
        and ATCUD, no VAT (I1:0) and no amounts (PT-52), the signature's short form and the certificate.
        """
        picking = self.deliver()
        self.assertEqual(self.qr_fields(picking), {
            'A': '123456789',
            'B': '501964843',
            'C': 'PT',
            'D': 'GT',
            'E': 'N',
            'F': '20260615',
            'G': 'GT 2026/00001',
            'H': f'{self.series_gt.at_code}-1',
            'I1': '0',
            'N': '0.00',
            'O': '0.00',
            'Q': picking.l10n_pt_inalterable_hash_short,
            'R': PT_CERTIFICATION_NUMBER,
        })
        self.assertEqual(len(picking.l10n_pt_inalterable_hash_short), 4)

    def test_qr_code_customer(self):
        """
        A foreign customer's NIF is as collected (PT-74); goods sent to a delivery contact name its
        company, the SAF-T's customer, whatever the contact's country (PT-38, PT-142); a return note is
        typed GD.
        """
        delivery = self.deliver(partner=self.partner_foreign)
        self.assertQrFields(delivery, {'B': '0477472701', 'C': 'BE', 'D': 'GT'})
        contact = self.env['res.partner'].create({
            'name': 'Armazém Madrid',
            'type': 'delivery',
            'parent_id': self.partner_pt.id,
            'country_id': self.env.ref('base.es').id,
        })
        self.assertQrFields(self.deliver(partner=contact), {'B': '501964843', 'C': 'PT'})
        receipt = self.deliver(self.in_type, partner=self.partner_supplier)
        supplier_return = self.validate(self.make_return(receipt))
        self.assertQrFields(supplier_return, {'B': '502011378', 'C': 'PT', 'D': 'GD', 'G': 'GD 2026/00001', 'I1': '0'})

    def test_qr_code_move_between_warehouses(self):
        """The QR code of a move between own warehouses names the company as customer, as its print does (PT-142)."""
        picking = self.deliver(self.int_type, partner=False, location_dest=self.warehouse_2.lot_stock_id)
        self.assertQrFields(picking, {'A': '123456789', 'B': '123456789', 'C': 'PT', 'D': 'GT'})
