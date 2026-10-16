from .common import PdpTestCommon


class TestPdpTransmissionTypes(PdpTestCommon):
    def test_co_flow_created_for_new_period_moves(self):
        """Complementary flow when a new invoice appears after an IN was sent."""
        first_invoice = self._create_invoice(sent=True)
        flows = self._aggregate_company()
        tx_flow = flows.filtered(lambda f: f.report_kind == "transaction")[:1]
        self.assertTrue(tx_flow, "Initial transaction flow should be created")
        tx_flow.action_send()

        new_invoice = self._create_invoice(sent=True, date_val=first_invoice.invoice_date)
        flows = self._aggregate_company()
        co_flow = flows.filtered(lambda f: f.report_kind == "transaction" and f.id != tx_flow.id)
        if not co_flow:
            co_flow = self.env["l10n.fr.pdp.flow"].search([
                ("company_id", "=", self.company.id),
                ("report_kind", "=", "transaction"),
                ("id", "!=", tx_flow.id),
            ], order="id desc")[:1]

        self.assertTrue(co_flow, "Complementary flow should be created for new moves in the same period")
        self.assertEqual(co_flow.transmission_type, "CO")
        self.assertFalse(co_flow.is_correction)
        self.assertFalse(co_flow.transmission_reference)
        self.assertEqual(set(co_flow.move_ids.ids), {new_invoice.id})

    def test_payment_mo_flow_sets_reference(self):
        """Payment flows overlapping a sent flow become MO with reference set."""
        inv1 = self._create_invoice(sent=True)
        self._create_payment_for_invoice(inv1)
        flows = self._aggregate_company()
        first_payment_flow = flows.filtered(lambda f: f.report_kind == "payment")[:1]
        self.assertTrue(first_payment_flow, "Initial payment flow should exist")
        first_payment_flow.action_send()
        self.assertTrue(first_payment_flow.transport_identifier)

        inv2 = self._create_invoice(sent=True)
        self._create_payment_for_invoice(inv2)
        flows = self._aggregate_company()
        mo_flow = flows.filtered(lambda f: f.report_kind == "payment" and f.id != first_payment_flow.id)
        if not mo_flow:
            mo_flow = self.env["l10n.fr.pdp.flow"].search([
                ("company_id", "=", self.company.id),
                ("report_kind", "=", "payment"),
                ("id", "!=", first_payment_flow.id),
            ], order="id desc")
        mo_flow = mo_flow and mo_flow[-1:]

        self.assertTrue(mo_flow, "MO payment flow should be created when moves overlap a sent flow")
        self.assertEqual(mo_flow.transmission_type, "MO")
        self.assertTrue(mo_flow.is_correction)
        self.assertEqual(mo_flow.transmission_reference, first_payment_flow.transport_identifier)
        self.assertEqual(mo_flow.transmission_reference_type, first_payment_flow.transmission_type)

    def test_rectificative_flow_action_creates_link(self):
        """Rectificative button should spawn RE flow referencing the sent flow."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        self.assertTrue(flow, "Transaction flow should be built")
        flow.action_send()
        action = flow.action_create_rectificative_flow()
        new_flow = self.env[action["res_model"]].browse(action["res_id"])

        self.assertEqual(new_flow.transmission_type, "RE")
        self.assertTrue(new_flow.is_correction)
        self.assertEqual(new_flow.transmission_reference, flow.transport_identifier)
        self.assertEqual(new_flow.transmission_reference_type, flow.transmission_type)
        self.assertEqual(set(new_flow.move_ids.ids), set(flow.move_ids.ids))
        self.assertEqual(new_flow.state, "draft")

    def test_payment_flow_not_duplicated_for_same_moves(self):
        """No new payment flow when move set is identical to the last sent one."""
        inv = self._create_invoice(sent=True)
        self._create_payment_for_invoice(inv)
        flows = self._aggregate_company()
        pay_flow = flows.filtered(lambda f: f.report_kind == "payment")[:1]
        self.assertTrue(pay_flow, "Payment flow should be present before send")
        pay_flow.action_send()

        count_before = self.env["l10n.fr.pdp.flow"].search_count([
            ("company_id", "=", self.company.id),
            ("report_kind", "=", "payment"),
        ])
        self._aggregate_company()
        count_after = self.env["l10n.fr.pdp.flow"].search_count([
            ("company_id", "=", self.company.id),
            ("report_kind", "=", "payment"),
        ])
        self.assertEqual(count_after, count_before, "Identical payment set must not spawn a new flow")

    def test_transaction_mo_flow_sets_reference(self):
        """Changing a sent invoice spawns a corrective MO flow with reference."""
        inv = self._create_invoice(sent=True)
        first_flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        self.assertTrue(first_flow)
        first_flow.action_send()
        self.assertTrue(first_flow.transport_identifier)

        # Modify a tracked field on the move to trigger corrective flow creation.
        inv.write({"invoice_line_ids": [(1, inv.invoice_line_ids[0].id, {"price_unit": inv.invoice_line_ids[0].price_unit + 10})]})
        mo_flow = self.env["l10n.fr.pdp.flow"].search([
            ("company_id", "=", self.company.id),
            ("report_kind", "=", "transaction"),
            ("is_correction", "=", True),
            ("transmission_type", "=", "MO"),
        ], order="id desc")[:1]

        self.assertTrue(mo_flow, "MO transaction flow should be created when a sent invoice changes")
        self.assertEqual(mo_flow.transmission_type, "MO")
        self.assertTrue(mo_flow.is_correction)
        self.assertEqual(mo_flow.transmission_reference, first_flow.transport_identifier)
        self.assertEqual(mo_flow.transmission_reference_type, first_flow.transmission_type)

    def test_transaction_flow_not_duplicated_for_same_moves(self):
        """No new transaction flow when the sent set is unchanged."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == "transaction")[:1]
        flow.action_send()
        count_before = self.env["l10n.fr.pdp.flow"].search_count([
            ("company_id", "=", self.company.id),
            ("report_kind", "=", "transaction"),
        ])
        self._aggregate_company()
        count_after = self.env["l10n.fr.pdp.flow"].search_count([
            ("company_id", "=", self.company.id),
            ("report_kind", "=", "transaction"),
        ])
        self.assertEqual(count_after, count_before, "Identical transaction set must not spawn a new flow")
