from odoo import Command
from odoo.addons.l10n_eg_edi_eta.tools.eta_serialize import compute_eta_uuid
from odoo.tests import tagged

from .common import TestL10nEgEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEgEdiPosPayloadBuilders(TestL10nEgEdiPosCommon):

    def test_refund_has_receipt_type_r_and_reference_uuid(self):
        """A refund's payload has ``documentType.receiptType == 'r'`` and
        ``header.referenceUUID == original.l10n_eg_edi_pos_uuid``."""
        original = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(original)
        original_uuid = original.l10n_eg_edi_pos_uuid
        refund = self._refund_of(original)

        payload = refund._l10n_eg_edi_pos_build_receipt()
        self.assertEqual(payload['documentType']['receiptType'], 'r')
        self.assertEqual(payload['header']['referenceUUID'], original_uuid)

    def test_resend_with_existing_uuid_has_reference_old_uuid(self):
        """When the order already has ``l10n_eg_edi_pos_uuid`` set, the next
        payload carries it as ``header.referenceOldUUID``."""
        order = self._create_unpaid_order()
        order.l10n_eg_edi_pos_uuid = 'PREVIOUS-UUID'
        payload = order._l10n_eg_edi_pos_build_receipt()
        self.assertEqual(payload['header']['referenceOldUUID'], 'PREVIOUS-UUID')

    def test_exchange_rate_zero_when_same_currency(self):
        """When order currency equals company currency, ``header.exchangeRate``
        is 0 (the rate field is unused)."""
        order = self._create_unpaid_order()
        self.assertEqual(order.currency_id, self.env.company.currency_id)
        payload = order._l10n_eg_edi_pos_build_receipt()
        self.assertEqual(payload['header']['exchangeRate'], 0)

    def test_exchange_rate_computed_when_different_currency(self):
        """Foreign-currency order — ``header.exchangeRate`` equals
        ``abs(converted_local_amount / amount_total)`` (EGP per foreign unit)."""
        self.pos_config_eur.journal_id.write({
            'l10n_eg_branch_id': self.eg_branch_partner.id,
            'l10n_eg_branch_identifier': '0',
            'l10n_eg_activity_type_id': self.env.ref('l10n_eg_edi_eta.l10n_eg_activity_type_8121').id,
        })
        self.pos_config_eur.sudo().write({
            'l10n_eg_edi_pos_enable': True,
            'l10n_eg_edi_pos_preprod': True,
            'l10n_eg_edi_pos_client_id': 'x',
            'l10n_eg_edi_pos_client_secret': 'x',
            'l10n_eg_edi_pos_serial_number': 'x',
        })
        eur = self.env.ref('base.EUR')
        eur.rate_ids.unlink()
        self.env['res.currency.rate'].create({
            'rate': 2.0,
            'currency_id': eur.id,
            'company_id': self.env.company.id,
            'name': '2020-01-01',
        })
        order, _ = self.create_backend_pos_order({
            'pos_config': self.pos_config_eur,
            'line_data': [{'product_id': self.eg_product_untaxed.product_variant_id.id, 'qty': 1.0}],
            'order_data': {'partner_id': self.eg_individual_customer.id},
        })

        payload = order._l10n_eg_edi_pos_build_receipt()
        self.assertAlmostEqual(payload['header']['exchangeRate'], 0.5)

    def test_foreign_partner_buyer_type_f_omits_id_keeps_name(self):
        """Non-EG partner → ``buyer.type == 'F'``: name is populated but no
        ``id`` is emitted for foreign buyers."""
        order = self._create_unpaid_order(partner=self.foreign_customer)
        payload = order._l10n_eg_edi_pos_build_receipt()
        self.assertEqual(payload['buyer']['type'], 'F')
        self.assertNotIn('id', payload['buyer'])
        self.assertEqual(payload['buyer']['name'], self.foreign_customer.name)

    def test_domestic_person_above_threshold_includes_vat_and_name(self):
        """Domestic 'P' partner with total ≥ threshold → buyer includes
        ``id`` (vat) and ``name``."""
        self.env.company.l10n_eg_invoicing_threshold = 1.0
        order = self._create_unpaid_order()
        payload = order._l10n_eg_edi_pos_build_receipt()
        self.assertEqual(payload['buyer']['type'], 'P')
        self.assertEqual(payload['buyer']['id'], self.eg_individual_customer._get_additional_identifier('EG_NIN'))
        self.assertEqual(payload['buyer']['name'], self.eg_individual_customer.name)

    def test_domestic_person_below_threshold_omits_vat_and_name(self):
        """Domestic 'P' partner with total < threshold → buyer only has
        ``type`` and ``paymentNumber``."""
        order = self._create_unpaid_order()
        payload = order._l10n_eg_edi_pos_build_receipt()
        self.assertEqual(payload['buyer']['type'], 'P')
        self.assertNotIn('id', payload['buyer'])
        self.assertNotIn('name', payload['buyer'])

    def test_discount_between_0_and_100_uses_discounted_price(self):
        """A line with discount in (0, 100) computes taxableItem amounts on
        ``price_unit * (1 - discount/100)``."""
        order = self._create_unpaid_order(lines=[
            {'product_id': self.eg_product_untaxed.product_variant_id.id, 'qty': 1.0, 'discount': 10.0},
        ])
        payload = order._l10n_eg_edi_pos_build_receipt()
        item = payload['itemData'][0]
        self.assertAlmostEqual(item['netSale'], 9.0)
        self.assertAlmostEqual(item['totalSale'], 10.0)

    def test_discount_at_zero_or_100_uses_full_price(self):
        """At discount 0 and 100, rate_before_discount stays 1, so totalSale is
        not scaled up and equals netSale (100% must not divide by zero)."""
        no_discount = self._create_unpaid_order(lines=[
            {'product_id': self.eg_product_untaxed.product_variant_id.id, 'qty': 1.0, 'discount': 0.0},
        ])
        payload = no_discount._l10n_eg_edi_pos_build_receipt()
        item = payload['itemData'][0]
        self.assertAlmostEqual(item['netSale'], item['totalSale'])
        self.assertAlmostEqual(item['netSale'], 10.0)

        full_discount = self._create_unpaid_order(lines=[
            {'product_id': self.eg_product_untaxed.product_variant_id.id, 'qty': 1.0, 'discount': 100.0},
        ])
        full_item = full_discount._l10n_eg_edi_pos_build_receipt()['itemData'][0]
        self.assertAlmostEqual(full_item['netSale'], 0.0)
        self.assertAlmostEqual(full_item['totalSale'], 0.0)

    def test_negative_line_routed_to_global_discounts(self):
        """On a non-refund order, a negative-amount line lands in
        ``extraReceiptDiscountData``, not in ``itemData``."""
        order = self._create_unpaid_order(lines=[
            {'product_id': self.eg_product_untaxed.product_variant_id.id, 'qty': 1.0},
            {'product_id': self.eg_product_untaxed.product_variant_id.id, 'qty': 1.0, 'price_unit': -3.0},
        ])
        payload = order._l10n_eg_edi_pos_build_receipt()
        self.assertEqual(len(payload['itemData']), 1)
        self.assertEqual(len(payload['extraReceiptDiscountData']), 1)

    def test_multi_tax_line_produces_separate_taxable_items(self):
        """A line with two taxes produces two entries in its
        ``taxableItems`` block, one per tax type."""
        self.eg_product_untaxed.taxes_id = [Command.set([self.eg_tax_vat.id, self.eg_tax_table.id])]
        order = self._create_unpaid_order()
        payload = order._l10n_eg_edi_pos_build_receipt()
        taxable_items = payload['itemData'][0]['taxableItems']
        self.assertEqual(len(taxable_items), 2)
        rate_by_type = {item['taxType']: item['rate'] for item in taxable_items}
        self.assertEqual(rate_by_type['T1'], 14.0)
        self.assertEqual(rate_by_type['T3'], 0)

    def test_uuid_is_reproducible_for_identical_payload(self):
        """``compute_eta_uuid`` is deterministic — two calls on the same
        payload return identical SHA-256 digests."""
        payload = {'header': {'uuid': ''}, 'value': 42, 'items': [{'a': 1}]}
        self.assertEqual(compute_eta_uuid(payload), compute_eta_uuid(payload))

    def test_refund_negative_line_stays_in_item_data(self):
        """On a refund, a negative-qty line stays in ``itemData`` — the
        negative-line routing only applies to non-refund orders."""
        original = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(original)
        refund = self._refund_of(original)
        self.assertTrue(any(line.qty < 0 for line in refund.lines))

        payload = refund._l10n_eg_edi_pos_build_receipt()
        self.assertEqual(len(payload['itemData']), 1)
        self.assertEqual(payload['extraReceiptDiscountData'], [])
