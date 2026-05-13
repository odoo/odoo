from odoo import Command
from odoo.tests import tagged

from .common import TestL10nEgEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEgEdiPosCheckData(TestL10nEgEdiPosCommon):

    def test_refund_original_not_sent_returns_error(self):
        """A refund whose source order is not in sent[_test] is rejected:
        check_data returns a non-empty error list."""
        original = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_response_error()):
            self._pay(original)
        self.assertEqual(original.l10n_eg_edi_pos_state, 'error_test')

        refund = self._refund_of(original)
        errors = refund._l10n_eg_edi_pos_check_data()
        self.assertTrue(any('original receipt must be submitted' in e for e in errors))

    def test_refund_partner_mismatch_returns_error(self):
        """A refund whose partner differs from the original receipt's partner
        is rejected by check_data."""
        original = self._create_unpaid_order(partner=self.eg_individual_customer)
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(original)
        refund = self._refund_of(original)
        refund.partner_id = self.eg_other_customer

        errors = refund._l10n_eg_edi_pos_check_data()
        self.assertTrue(any('must match' in e for e in errors))

    def test_non_refund_with_negative_line_returns_error(self):
        """A new sale containing a negative-quantity line is rejected — negatives
        are only allowed on refund orders."""
        order = self._create_unpaid_order(lines=[
            {'product_id': self.eg_product_untaxed.product_variant_id.id, 'qty': 1.0},
            {'product_id': self.eg_product_untaxed.product_variant_id.id, 'qty': -1.0},
        ])
        errors = order._l10n_eg_edi_pos_check_data()
        self.assertTrue(any('Negative quantities' in e for e in errors))

    def test_threshold_domestic_person_no_vat_returns_error(self):
        """Above-threshold sales to a domestic individual without a VAT trip
        the threshold guard and are rejected."""
        self.env.company.l10n_eg_invoicing_threshold = 1.0
        self.eg_individual_customer._set_additional_identifier('EG_NIN', False)
        order = self._create_unpaid_order()
        errors = order._l10n_eg_edi_pos_check_data()
        self.assertTrue(any('National ID' in e for e in errors))

    def test_threshold_domestic_person_with_vat_passes(self):
        """Same above-threshold case but the individual has a VAT — check_data
        returns no threshold error."""
        self.env.company.l10n_eg_invoicing_threshold = 1.0
        order = self._create_unpaid_order()
        errors = order._l10n_eg_edi_pos_check_data()
        self.assertFalse(any('National ID' in e for e in errors))

    def test_branch_vat_equals_partner_vat_returns_error(self):
        """The branch and the customer cannot share the same VAT — check_data
        flags the collision."""
        self.eg_individual_customer.vat = self.eg_branch_partner.vat
        order = self._create_unpaid_order()
        errors = order._l10n_eg_edi_pos_check_data()
        self.assertTrue(any('same VAT' in e for e in errors))

    def test_branch_address_missing_field_returns_error(self):
        """Stripping any of country/state/city/street/building_no on the branch
        fails ``_l10n_eg_validate_info_address`` and is reported by check_data."""
        self.eg_branch_partner.city = False
        order = self._create_unpaid_order()
        errors = order._l10n_eg_edi_pos_check_data()
        self.assertTrue(any('address' in e for e in errors))

    def test_tax_without_eta_code_returns_error(self):
        """A line whose tax has no ``l10n_eg_eta_code`` is rejected — the payload
        builder cannot derive taxType/subType without it."""
        self.eg_product_untaxed.taxes_id = [Command.set(self.eg_tax_uncoded.ids)]
        order = self._create_unpaid_order()
        errors = order._l10n_eg_edi_pos_check_data()
        self.assertTrue(any('ETA tax code' in e for e in errors))

    def test_uom_without_unit_code_returns_error(self):
        """A line whose UoM has no ``l10n_eg_unit_code_id.code`` is rejected —
        the payload builder needs it for ``itemData[].unitType``."""
        self.env.ref('uom.product_uom_unit').l10n_eg_unit_code_id = False
        order = self._create_unpaid_order()
        errors = order._l10n_eg_edi_pos_check_data()
        self.assertTrue(any('unit-of-measure' in e for e in errors))

    def test_all_valid_returns_empty(self):
        """Happy path with every fixture intact — check_data returns []."""
        order = self._create_unpaid_order()
        self.assertEqual(order._l10n_eg_edi_pos_check_data(), [])
