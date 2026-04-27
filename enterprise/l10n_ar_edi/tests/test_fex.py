# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import skip_unless_external
from odoo.addons.l10n_ar_edi.tests.common import TestArEdiCommon
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install', *TestArEdiCommon.extra_tags)
class TestArEdiWsfex(TestArEdiCommon):

    @classmethod
    @TestArEdiCommon.setup_afip_ws('wsfex')
    def setUpClass(cls):
        super().setUpClass()
        cls.subfolder = "wsfex"
        cls.partner = cls.res_partner_barcelona_food
        cls.incoterm = cls.env.ref('account.incoterm_EXW')
        cls.journal = cls._create_journal('wsfex')

        # Document Types
        cls.document_type.update({
            'invoice_e': cls.env.ref('l10n_ar.dc_e_f'),
            'credit_note_e': cls.env.ref('l10n_ar.dc_e_nc'),
        })

    @classmethod
    def _create_invoice_ar(cls, **invoice_args):
        # EXTEND TestArEdiCommon._create_invoice_ar
        invoice_args.setdefault('invoice_incoterm_id', cls.incoterm)
        return super()._create_invoice_ar(**invoice_args)

    @skip_unless_external
    def test_ar_edi_wsfex_external_flow(self):
        self._test_ar_edi_common_external()

    def test_ar_edi_wsfex_flow_suite(self):
        for test_name, move_type, document_code, concept in (
                ('test_wsfex_invoice_e_product', 'invoice', 'e', 'product'),
                ('test_wsfex_invoice_e_service', 'invoice', 'e', 'service'),
                ('test_wsfex_invoice_e_product_service_default', 'invoice', 'e', 'product_service'),
                ('test_wsfex_credit_note_e_product', 'credit_note', 'e', 'product'),
                ('test_wsfex_credit_note_e_service', 'credit_note', 'e', 'service'),
                ('test_wsfex_credit_note_e_product_service', 'credit_note', 'e', 'product_service'),
        ):
            with self.subTest(test_name=test_name), self.cr.savepoint() as sp:
                self._test_ar_edi_flow(test_name, move_type, document_code, concept)
                sp.close()  # Rollback to ensure all subtests start in the same situation

    def test_ar_edi_wsfex_invoice_free_zone(self):
        """ Invoice to "IVA Liberado - Free Zone" partner (similar to demo_invoice_6) """
        invoice = self._test_ar_edi_flow(
            test_name='test_wsfex_invoice_free_zone',
            move_type='invoice',
            document_code='e',
            concept='product_service',
            partner_id=self.res_partner_montana_sur,
            invoice_line_ids=self._get_ar_multi_invoice_line_ids(),
        )
        self.assertEqual(set(invoice.invoice_line_ids.tax_ids.mapped('amount')), {0.0})

    def test_ar_edi_wsfex_invoice_e_product_service(self):
        """ Invoice "4 - Otros (expo)" because it have Services (similar to demo_invoice_7) """
        # Can be unified with test_04_invoice_e_product_service? why 4 - Otros (expo)?
        invoice = self._test_ar_edi_flow(
            test_name='test_wsfex_invoice_e_product_service_multi',
            move_type='invoice',
            document_code='e',
            concept='product_service',
            partner_id=self.res_partner_barcelona_food,
            invoice_line_ids=self._get_ar_multi_invoice_line_ids(),
        )
        self.assertEqual(set(invoice.invoice_line_ids.tax_ids.mapped('amount')), {0.0})

    def test_ar_edi_wsfex_invoice_with_notes(self):
        """ Invoice with multiple products/services and with line note """
        note_line_values = self._prepare_invoice_line(display_type='line_note', price_unit=False, product_id=False, name='Notes')
        invoice = self._test_ar_edi_flow(
            test_name='test_wsfex_invoice_e_with_notes',
            move_type='invoice',
            document_code='e',
            concept='product_service',
            partner_id=self.res_partner_barcelona_food,
            invoice_line_ids=self._get_ar_multi_invoice_line_ids() + [note_line_values],
        )
        self.assertEqual(set(invoice.invoice_line_ids.tax_ids.mapped('amount')), {0.0})

    def test_ar_edi_wsfex_payment_foreign_currency(self):
        """ Payment in Foreign Currency  """
        self._test_payment_foreign_currency()
