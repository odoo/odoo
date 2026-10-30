from odoo.tests import tagged

from odoo.addons.l10n_pt_pos.tests.common import TestL10nPtPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtPosPrinting(TestL10nPtPosCommon):
    """
    The till's receipt is a print of the order's invoice: it carries the invoice's designation,
    number, ATCUD, the four characters of its signature and its QR code (Despacho 8632/2014 2.2.4,
    Portaria 195/2020 art. 6), and counts towards its prints -- one Original, then copies marked
    '2ª Via', whether printed at the till or in the back office (Despacho 8632/2014 2.2.15).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.session = cls.open_session()

    # -------------------------------------------------------------------------
    # Receipt
    # -------------------------------------------------------------------------

    def test_receipt_values(self):
        """The receipt shows the invoice's designation, number, ATCUD, short signature and raw QR string."""
        order = self.sell()
        invoice = order.account_move
        self.assertEqual(self.receipt(order), {
            'name': order.name,
            'hash_short': invoice.l10n_pt_inalterable_hash_short,
            'atcud': f'{self.series_fs.at_code}-1',
            'document_identifier': 'FS 2026/00001',
            'qr_code_str': invoice.l10n_pt_qr_code_str,
            'is_reprint': False,
            'document_type': 'Fatura simplificada',
            'training_mode': False,
        })
        self.assertEqual(len(self.receipt(order)['hash_short']), 4)
        self.assertEqual(self.receipt(self.sell(partner=self.partner_pt))['document_type'], 'Fatura-recibo')

    def test_receipt_qr_string_raw(self):
        """The till encodes the QR string itself: it gets it raw, not URL-escaped (PT-24)."""
        qr_code_str = self.receipt(self.sell())['qr_code_str']
        self.assertRegex(qr_code_str, r'^A:123456789\*B:999999990\*C:PT\*D:FS\*E:N\*F:20260615\*G:FS 2026/00001\*H:')
        self.assertNotIn('%', qr_code_str)

    def test_receipt_before_invoice(self):
        """An order not invoiced yet, still open at the till, has nothing to print."""
        order = self.sync(self.order_data(state='draft', payment_ids=[]))
        self.assertFalse(order.account_move)
        self.assertEqual(self.receipt(order), {})

    def test_receipt_training_series(self):
        """A document of a training series is marked as such on the receipt."""
        self.series_fs.training_series = True
        self.assertTrue(self.receipt(self.sell())['training_mode'])

    # -------------------------------------------------------------------------
    # Print version
    # -------------------------------------------------------------------------

    def test_cashier_prints_receipt(self):
        """A cashier, without accounting rights, prints the receipt of a sale (PT-138)."""
        order = self.sell()
        self.print_receipt(order, user=self.cashier)
        self.assertEqual(order.account_move.l10n_pt_print_version, 'original')

    def test_till_print_then_reprints(self):
        """The first print at the till is the Original, every later one a reprint."""
        order = self.sell()
        self.print_receipt(order)
        self.assertEqual(order.account_move.l10n_pt_print_version, 'original')
        self.assertTrue(self.receipt(order)['is_reprint'])
        self.print_receipt(order)
        self.assertEqual(order.account_move.l10n_pt_print_version, 'reprint')

    def test_one_original_across_till_and_back_office(self):
        """
        The receipt and the invoice PDF are prints of one document: after the till's Original the
        back office prints a 2ª Via, and after the back office's Original the till prints a reprint
        (PT-70).
        """
        till_first = self.sell()
        self.print_receipt(till_first)
        self.assertIn('2ª Via', self.print_pdf(till_first.account_move))

        back_office_first = self.sell()
        self.assertNotIn('2ª Via', self.print_pdf(back_office_first.account_move))
        self.assertTrue(self.receipt(back_office_first)['is_reprint'])

    def test_reprint_reason_logged(self):
        """The reason the cashier gives for a reprint is logged on the order."""
        order = self.sell()
        order.with_user(self.cashier).post_reprint_reason("Papel encravado")
        self.assertIn("Papel encravado", order.message_ids[0].body)
        self.assertIn(order.name, order.message_ids[0].body)

    # -------------------------------------------------------------------------
    # QR code
    # -------------------------------------------------------------------------

    def test_qr_customer(self):
        """
        An FS to 'Consumidor final' codes its generic NIF; an FR to a foreign customer codes its tax
        number as collected (PT-74).
        """
        self.assertQrFields(self.sell().account_move, {'B': '999999990', 'C': 'PT', 'D': 'FS'})
        self.assertQrFields(self.sell(partner=self.partner_foreign).account_move, {'B': '0477472701', 'C': 'BE', 'D': 'FR'})
