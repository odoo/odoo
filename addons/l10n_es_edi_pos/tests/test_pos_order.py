# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestL10nEsEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiPosOrder(TestL10nEsEdiPosCommon):

    def _get_simplified_invoice_name(self, order):
        return f"{self.config.id}/{str(order.sequence_number).zfill(6)}"

    # -------------------------------------------------------------------------
    # NUMBERING OF THE SIMPLIFIED INVOICES
    # -------------------------------------------------------------------------

    def test_simplified_invoice_number_assigned_at_payment(self):
        self.open_new_session(0.0)
        draft = self._create_draft()
        self.assertEqual(draft.sequence_number, 0, "A draft is not issued yet: it has no number")

        order = self._create_sale()
        self.assertTrue(order.sequence_number)

    def test_simplified_invoice_series_without_gaps(self):
        """ Neither a cancelled draft (e.g. a restaurant table) nor an invoiced order
        consume a number of the series of simplified invoices. """
        self.open_new_session(0.0)
        first = self._create_sale()

        draft = self._create_draft()
        draft.action_pos_order_cancel()
        invoiced = self._create_sale(is_invoiced=True, customer=self.partner_b)

        last = self._create_sale()
        self.assertEqual(draft.sequence_number, 0)
        self.assertEqual(invoiced.sequence_number, 0)
        self.assertEqual(last.sequence_number, first.sequence_number + 1)

    def test_standard_numbering_without_fiscal_mode(self):
        """ Without fiscal mode, the orders are numbered at creation, as in the standard POS. """
        self.open_new_session(0.0)
        with self._patch_fiscal_mode(False):
            draft = self._create_draft()
        self.assertTrue(draft.sequence_number)

    # -------------------------------------------------------------------------
    # LIMIT OF THE SIMPLIFIED INVOICES
    # -------------------------------------------------------------------------

    def test_simplified_invoice_limit(self):
        self.company.l10n_es_simplified_invoice_limit = 242.0  # 2 products
        self.open_new_session(0.0)

        with self.subTest(case="draft above the limit"):
            # Not issued yet: whether it will be invoiced is only known at payment.
            self._create_draft(quantity=3)

        with self.subTest(case="amount equal to the limit"):
            self._create_sale(quantity=2)

        with self.subTest(case="invoiced order above the limit"):
            self._create_sale(quantity=3, is_invoiced=True, customer=self.partner_b)

        with self.subTest(case="simplified invoice above the limit"), self.assertRaises(UserError):
            self._create_sale(quantity=3)

    # -------------------------------------------------------------------------
    # NUMBER SHOWN ON THE RECEIPT
    # -------------------------------------------------------------------------

    def test_invoice_name(self):
        self.open_new_session(0.0)
        order = self._create_sale()
        invoiced = self._create_sale(is_invoiced=True, customer=self.partner_b)
        draft = self._create_draft()

        self.assertEqual(order._l10n_es_pos_get_invoice_name(), self._get_simplified_invoice_name(order))
        self.assertEqual(invoiced._l10n_es_pos_get_invoice_name(), invoiced.account_move.name)
        self.assertEqual(draft._l10n_es_pos_get_invoice_name(), '')

    def test_invoice_name_after_session_closing(self):
        """ Once the session is closed, `account_move` is the session closing entry for the
        orders that were not invoiced: they keep showing their simplified invoice number. """
        with self.with_pos_session():
            order = self._create_sale()

        self.assertTrue(order.is_globally_invoiced)
        self.assertEqual(order._l10n_es_pos_get_invoice_name(), self._get_simplified_invoice_name(order))

    # -------------------------------------------------------------------------
    # REFUNDs
    # -------------------------------------------------------------------------

    def test_refund_reasons(self):
        """ The selection is dynamic: the reasons must not be read from `selection_ids`,
        which are empty for such a selection. """
        reasons = self.env['pos.order']._l10n_es_pos_get_refund_reasons()
        self.assertEqual({reason['value'] for reason in reasons}, {'R1', 'R2', 'R3', 'R4', 'R5'})
        self.assertTrue(all(reason['name'] for reason in reasons))

    def test_refund_sequence_created_with_the_pos(self):
        new_config = self.env['pos.config'].create({'name': 'Second shop'})
        self.assertTrue(self.config.l10n_es_pos_refund_sequence_id)
        self.assertTrue(new_config.l10n_es_pos_refund_sequence_id)
        self.assertNotEqual(new_config.l10n_es_pos_refund_sequence_id, self.config.l10n_es_pos_refund_sequence_id)

    def test_simplified_credit_note_number(self):
        self.open_new_session(0.0)
        refund = self._create_refund(self._create_sale())

        self.assertEqual(refund.sequence_number, 0, "A refund takes no number of the series of simplified invoices")
        self.assertTrue(refund.l10n_es_pos_refund_sequence_number)
        self.assertEqual(
            refund._l10n_es_pos_get_invoice_name(),
            f"R{str(self.config.id).zfill(2)}/{str(refund.l10n_es_pos_refund_sequence_number).zfill(6)}",
        )

    def test_simplified_credit_note_series(self):
        """ Simplified invoices and simplified credit notes are numbered in their own series,
        without gaps in any of them. """
        self.open_new_session(0.0)
        first_order = self._create_sale()
        first_refund = self._create_refund(first_order)
        last_order = self._create_sale()
        last_refund = self._create_refund(last_order)

        self.assertEqual(last_order.sequence_number, first_order.sequence_number + 1)
        self.assertEqual(
            last_refund.l10n_es_pos_refund_sequence_number,
            first_refund.l10n_es_pos_refund_sequence_number + 1,
        )

    def test_invoiced_refund_takes_no_number(self):
        """ A refund paid to be invoiced gets an invoice number: no simplified credit note number.
        All the refunds are invoiced with SII, and the refunds of invoiced orders with TicketBAI
        and Veri*Factu. """
        self.open_new_session(0.0)
        order = self._create_sale(is_invoiced=True, customer=self.partner_b)
        refund = self.env['pos.order'].browse(order.refund()['res_id'])
        refund.to_invoice = True
        self.make_payment(refund, self.bank_pm1, refund.amount_total)

        self.assertTrue(refund.is_singly_invoiced)
        self.assertFalse(refund.sequence_number)
        self.assertFalse(refund.l10n_es_pos_refund_sequence_number)
        self.assertEqual(refund._l10n_es_pos_get_invoice_name(), refund.account_move.name)

    def test_refund_numbering_without_fiscal_mode(self):
        """ Without fiscal mode, refunds are numbered as any order, as in the standard POS. """
        self.open_new_session(0.0)
        with self._patch_fiscal_mode(False):
            refund = self._create_refund(self._create_sale())
        self.assertTrue(refund.sequence_number)
        self.assertFalse(refund.l10n_es_pos_refund_sequence_number)
