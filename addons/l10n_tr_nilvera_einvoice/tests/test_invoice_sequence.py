from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nTrInvoiceSequence(TestUBLTRCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_journal = cls.company_data['default_journal_sale']
        cls.purchase_journal = cls.company_data['default_journal_purchase']
        cls.einvoice_partner_2 = cls.env['res.partner'].create({
            'name': 'Test Partner 2',
            'l10n_tr_nilvera_customer_status': 'einvoice',
        })

    def _add_sequence(self, name, journal=None, **conditions):
        return self.env['l10n_tr_nilvera_einvoice.invoice.sequence'].create({
            'journal_id': (journal or self.sale_journal).id,
            'name': name,
            **conditions,
        })

    def _create_invoice_tr(self, move_type='out_invoice', partner=None, journal=None, post=True, **values):
        return self._create_invoice(
            move_type=move_type,
            journal_id=journal or self.sale_journal,
            partner_id=partner or self.einvoice_partner,
            invoice_date='2025-03-05',
            invoice_line_ids=[self._prepare_invoice_line(name='line', price_unit=100.0)],
            post=post,
            **values,
        )

    def test_series_replace_the_journal_code_and_number_independently(self):
        """Each series takes over the journal code and keeps its own continuous numbering.

        The two series are interleaved on purpose: the numbering looks at the last document of
        the journal, so a series must not continue from the one posted just before it.
        """
        self._add_sequence('DOM')
        self._add_sequence('EXP', l10n_tr_is_export_invoice=True)

        first_domestic = self._create_invoice_tr()
        first_export = self._create_invoice_tr(l10n_tr_is_export_invoice=True)
        second_domestic = self._create_invoice_tr()
        second_export = self._create_invoice_tr(l10n_tr_is_export_invoice=True)

        self.assertEqual(first_domestic.name, 'DOM/2025/00001')
        self.assertEqual(second_domestic.name, 'DOM/2025/00002')
        self.assertEqual(first_export.name, 'EXP/2025/00001')
        self.assertEqual(second_export.name, 'EXP/2025/00002')

    def test_documents_without_a_series_keep_the_journal_numbering(self):
        """A document matching no series numbers on the journal, never on a series.

        Both halves matter: a journal with no series at all must number exactly as before, and
        once a series exists the fallback must not take the next number of that series.
        """
        first = self._create_invoice_tr()
        second = self._create_invoice_tr()
        self.assertEqual(first.name, f'{self.sale_journal.code}/2025/00001')
        self.assertEqual(second.name, f'{self.sale_journal.code}/2025/00002')

        self._add_sequence('EXP', l10n_tr_is_export_invoice=True)
        export = self._create_invoice_tr(l10n_tr_is_export_invoice=True)
        third = self._create_invoice_tr()
        self.assertEqual(export.name, 'EXP/2025/00001')
        self.assertEqual(third.name, f'{self.sale_journal.code}/2025/00003')

    def test_empty_conditions_match_anything_and_the_most_specific_series_wins(self):
        """An empty condition is a wildcard, and the series pinning the most wins.

        'ACM' and 'AKM' both name the customer, so ranking has to look past that first
        condition to tell them apart.
        """
        self._add_sequence('ANY')
        self._add_sequence('ACM', partner_id=self.einvoice_partner.id)
        self._add_sequence(
            'AKM', partner_id=self.einvoice_partner.id, l10n_tr_gib_invoice_scenario='KAMU',
        )

        other = self._create_invoice_tr(partner=self.einvoice_partner_2)
        public_other = self._create_invoice_tr(
            partner=self.einvoice_partner_2, l10n_tr_gib_invoice_scenario='KAMU',
        )
        named = self._create_invoice_tr(partner=self.einvoice_partner)
        public_named = self._create_invoice_tr(
            partner=self.einvoice_partner, l10n_tr_gib_invoice_scenario='KAMU',
        )

        self.assertEqual(other.name, 'ANY/2025/00001')
        self.assertEqual(public_other.name, 'ANY/2025/00002')
        self.assertEqual(named.name, 'ACM/2025/00001')
        self.assertEqual(public_named.name, 'AKM/2025/00001')

    def test_conditions_gib_determines_are_set_and_enforced(self):
        """Where GİB leaves no choice the series is filled in, and contradictions are refused."""
        export_series = self._add_sequence('EXP', l10n_tr_is_export_invoice=True)
        self.assertEqual(export_series.l10n_tr_gib_invoice_type, 'ISTISNA')
        self.assertFalse(export_series.l10n_tr_gib_invoice_scenario)

        bill_series = self._add_sequence('BIL', journal=self.purchase_journal)
        self.assertFalse(bill_series.l10n_tr_gib_invoice_type)
        self.assertFalse(bill_series.l10n_tr_gib_invoice_scenario)
        bill = self._create_invoice_tr(move_type='in_invoice', journal=self.purchase_journal)
        self.assertEqual(bill.name, 'BIL/2025/03/0001')

        with self.assertRaises(ValidationError):
            self._add_sequence('BAD', journal=self.purchase_journal, l10n_tr_gib_invoice_type='SATIS')

        return_series = self._add_sequence('RET', l10n_tr_gib_invoice_type='IADE')
        self.assertTrue(return_series.l10n_tr_is_credit_note)
        self.assertFalse(self._add_sequence('SAL').l10n_tr_is_credit_note)

        vendor_refunds = self._add_sequence(
            'BRT', journal=self.purchase_journal, l10n_tr_is_credit_note=True,
        )
        self.assertTrue(vendor_refunds.l10n_tr_is_credit_note)
