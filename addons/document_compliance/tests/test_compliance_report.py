from datetime import date, timedelta

from odoo.tests.common import TransactionCase

from .common import ComplianceCase


class TestComplianceReportAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env["document.compliance.report"]
        cls.user_plain = cls.env["res.users"].create(
            {
                "name": "Compliance Report Reader",
                "login": "test_compliance_reader",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def test_plain_internal_user_can_read_and_group_the_report(self):
        self.assertFalse(self.user_plain.has_group("base.group_erp_manager"))
        report = self.report.with_user(self.user_plain)

        self.assertIsInstance(report.search_count([]), int)
        report.search([], limit=5).mapped("entity_name")
        report._read_group([], ["entity_type"], ["__count"])

    def test_assembling_the_query_reads_no_model_metadata(self):
        queries = []
        execute = self.env.cr.execute

        def spy(query, params=None, *args, **kwargs):
            queries.append(query.code if hasattr(query, "code") else str(query))
            if params is not None:
                return execute(query, params, *args, **kwargs)
            return execute(query, *args, **kwargs)

        self.report.refresh()
        self.env.invalidate_all()
        self.env.cr.execute = spy
        try:
            self.report.search([], limit=80).mapped("entity_name")
        finally:
            self.env.cr.execute = execute

        self.assertFalse([query for query in queries if "ir_model" in query])


class TestComplianceReportScope(ComplianceCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env["document.compliance.report"]
        cls.env["document.type"].search([("is_mandatory", "=", True)]).write(
            {"is_mandatory": False}
        )
        cls.partner_type = cls._type(
            "SCOPE_PARTNER", is_mandatory=True, applies_to="res.partner"
        )
        cls.everyone_type = cls._type("SCOPE_ALL", is_mandatory=True, applies_to="all")
        cls.other_model_type = cls._type(
            "SCOPE_OTHER",
            is_mandatory=True,
            applies_to="hr.employee",
        )

    def _partner(self, name):
        return self.env["res.partner"].create({"name": name})

    def _partner_doc(self, partner, doc_type, days, **vals):
        return self._doc(
            doc_type,
            days,
            name=f"{partner.name} {doc_type.code}",
            res_model="res.partner",
            res_id=partner.id,
            **vals,
        )

    def _row_for(self, record):
        self._publish()
        return self.report.search(
            [("entity_type", "=", record._name), ("entity_id", "=", record.id)]
        )

    def test_an_entity_with_no_documents_still_has_a_row(self):
        row = self._row_for(self._partner("Documentless"))

        self.assertTrue(row)
        self.assertEqual(row.total_required, 2, "the partner type plus the all type")
        self.assertEqual(row.total_missing, 2)
        self.assertEqual(row.total_valid, 0)
        self.assertEqual(row.compliance_percentage, 0)
        self.assertEqual(row.compliance_state, "non_compliant")

    def test_a_type_scoped_to_another_model_is_not_required(self):
        row = self._row_for(self._partner("Scoped"))

        self.assertEqual(row.total_required, 2, self.other_model_type.code)

    def test_a_fully_covered_partner_is_compliant(self):
        partner = self._partner("Covered")
        for doc_type in (self.partner_type, self.everyone_type):
            self._partner_doc(partner, doc_type, 365)

        row = self._row_for(partner)

        self.assertEqual((row.total_required, row.total_valid), (2, 2))
        self.assertEqual(row.compliance_percentage, 100)
        self.assertTrue(row.is_compliant)
        self.assertEqual(row.compliance_state, "compliant")

    def test_a_type_lands_in_exactly_one_bucket(self):
        partner = self._partner("Buckets")
        self._partner_doc(partner, self.partner_type, -5)
        self._partner_doc(partner, self.partner_type, 5)
        self._partner_doc(partner, self.everyone_type, -5)

        row = self._row_for(partner)

        self.assertEqual(
            (row.total_valid, row.total_expiring, row.total_expired, row.total_missing),
            (0, 1, 1, 0),
            "an expiring document beats an expired one on the same type",
        )
        self.assertEqual(row.total_present, 2)
        self.assertEqual(row.earliest_expiry, date.today() - timedelta(days=5))

    def test_a_valid_document_hides_its_expired_siblings(self):
        partner = self._partner("Renewed")
        self._partner_doc(partner, self.partner_type, -5)
        self._partner_doc(partner, self.partner_type, 200)

        row = self._row_for(partner)

        self.assertEqual(
            (row.total_valid, row.total_expiring, row.total_expired), (1, 0, 0)
        )

    def test_another_companys_document_does_not_satisfy_the_requirement(self):
        other = self.env["res.company"].create({"name": "Other Co"})
        partner = self.env["res.partner"].create(
            {"name": "Local Partner", "company_id": self.company.id}
        )
        global_type = self.env["document.type"].create(
            {
                "name": "Global mandatory",
                "code": "GLOBAL_MAND",
                "is_mandatory": True,
                "company_id": False,
            }
        )
        self._partner_doc(partner, global_type, 365, company_id=other.id)

        row = self._row_for(partner)

        self.assertEqual(row.total_valid, 0)
        self.assertEqual(row.total_missing, row.total_required)

    def test_a_row_id_keeps_denoting_the_same_entity(self):
        high = self._partner("High Id")
        self._publish()
        before = {
            row.id: (row.entity_type, row.entity_id) for row in self.report.search([])
        }
        self.assertIn(high.id, [entity_id for _model, entity_id in before.values()])

        low = self.env["res.partner"].search([], order="id", limit=1)
        self._partner_doc(low, self.partner_type, 365)
        self._publish()
        after = {
            row.id: (row.entity_type, row.entity_id) for row in self.report.search([])
        }

        moved = {
            row_id: (before[row_id], after[row_id])
            for row_id in before
            if row_id in after and before[row_id] != after[row_id]
        }
        self.assertFalse(moved)

    def test_a_high_entity_id_does_not_break_the_report(self):
        self.env.cr.execute("SELECT last_value, is_called FROM res_partner_id_seq")
        last_value, is_called = self.env.cr.fetchone()
        self.addCleanup(
            self.env.cr.execute,
            "SELECT setval('res_partner_id_seq', %s, %s)",
            (last_value, is_called),
        )
        self.env.cr.execute(
            "SELECT setval('res_partner_id_seq', (SELECT MAX(id) FROM res_partner) + 3000000)"
        )
        partner = self._partner("Huge id")
        self.assertGreater(partner.id, 2_147_483)

        row = self._row_for(partner)

        self.assertEqual(row.entity_id, partner.id)
        self.assertTrue(self.report.search_count([]))

    def test_the_row_id_survives_a_reread_for_the_action_buttons(self):
        partner = self._partner("Button Partner")
        row_id = self._row_for(partner).id

        self.env.invalidate_all()
        action = self.report.browse(row_id).action_view_documents()

        self.assertIn(("res_id", "=", partner.id), action["domain"])
        self.assertIn(("res_model", "=", "res.partner"), action["domain"])
