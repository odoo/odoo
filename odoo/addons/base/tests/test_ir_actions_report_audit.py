from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestReportAuditFixes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reports = cls.env["ir.actions.report"].create(
            [
                {
                    "name": "Audit Report 1",
                    "model": "res.partner",
                    "report_name": "base.audit_report_1",
                },
                {
                    "name": "Audit Report 2",
                    "model": "res.partner",
                    "report_name": "base.audit_report_2",
                },
                {
                    "name": "Audit Report 3",
                    "model": "res.users",
                    "report_name": "base.audit_report_3",
                },
            ]
        )

    def test_create_action_binds_per_model(self):
        self.reports.create_action()
        partner_model = self.env["ir.model"]._get("res.partner")
        users_model = self.env["ir.model"]._get("res.users")
        self.assertEqual(self.reports[0].binding_model_id, partner_model)
        self.assertEqual(self.reports[1].binding_model_id, partner_model)
        self.assertEqual(self.reports[2].binding_model_id, users_model)
        self.assertEqual(set(self.reports.mapped("binding_type")), {"report"})

    def test_create_action_checks_write_access(self):
        user = self.env["res.users"].create(
            {
                "name": "Report Audit User",
                "login": "report_audit_user",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self.reports.with_user(user).create_action()

    def test_search_model_id_unhandled_combo_returns_notimplemented(self):
        Report = self.env["ir.actions.report"]
        self.assertIs(Report._search_model_id("=", None), NotImplemented)
        partner_model = self.env["ir.model"]._get("res.partner")
        found = Report.search([("model_id", "=", partner_model.id)])
        self.assertIn(self.reports[0], found)

    def test_render_unknown_report_type_raises(self):
        report = self.reports[0]
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE ir_act_report_xml SET report_type = %s WHERE id = %s",
            ["qweb-bogus", report.id],
        )
        report.invalidate_recordset(["report_type"])
        with self.assertRaises(UserError) as capture:
            self.env["ir.actions.report"]._render(report, [])
        self.assertIn("qweb-bogus", str(capture.exception))

    def test_render_resolves_string_reference_once(self):
        self.env["ir.actions.report"].create(
            {
                "name": "Audit Render Report",
                "model": "res.partner",
                "report_type": "qweb-html",
                "report_name": "base.audit_report_render",
            }
        )
        self.env["ir.ui.view"].create(
            {
                "type": "qweb",
                "name": "base.audit_report_render",
                "key": "base.audit_report_render",
                "arch": '<main><div class="article"><span>audit</span></div></main>',
            }
        )
        Report = self.env["ir.actions.report"]
        report_cls = type(Report)
        original_get_report = report_cls._get_report
        seen_refs = []

        def _tracking_get_report(model_self, report_ref):
            seen_refs.append(report_ref)
            return original_get_report(model_self, report_ref)

        self.patch(report_cls, "_get_report", _tracking_get_report)
        content, report_type = Report._render(
            "base.audit_report_render", [self.env.user.partner_id.id]
        )
        self.assertEqual(report_type, "html")
        self.assertIn(b"audit", content)
        string_refs = [ref for ref in seen_refs if isinstance(ref, str)]
        self.assertEqual(
            len(string_refs),
            1,
            "the string report reference must be resolved exactly once per render",
        )

    def test_barcode_fallback_to_code128_logs_warning(self):
        with self.assertLogs(
            "odoo.addons.base.models.ir_actions_report", level="WARNING"
        ) as capture:
            png = self.env["ir.actions.report"].prepare_barcode("I2of5", "not-numeric")
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertTrue(
            any("falling back to Code128" in line for line in capture.output)
        )

    def test_report_name_is_indexed(self):
        self.assertTrue(self.env["ir.actions.report"]._fields["report_name"].index)


@tagged("post_install", "-at_install")
class TestValidActionReportsDomainGuard(TransactionCase):
    def test_malformed_domain_is_logged_and_treated_valid(self):
        Report = self.env["ir.actions.report"]
        common = {
            "model": "res.partner",
            "report_type": "qweb-pdf",
        }
        good = Report.create(
            {
                "name": "audit good domain",
                "report_name": "base.audit_good_domain_dummy",
                "domain": "[('name', '=', 'Audit Domain Guard')]",
                **common,
            }
        )
        bad = Report.create(
            {
                "name": "audit bad domain",
                "report_name": "base.audit_bad_domain_dummy",
                "domain": "[('name' =",
                **common,
            }
        )
        partner = self.env["res.partner"].create({"name": "Audit Domain Guard"})
        with self.assertLogs(
            "odoo.addons.base.models.ir_actions_report", level="WARNING"
        ) as capture:
            valid_ids = (good + bad).get_valid_action_reports(
                "res.partner", [partner.id]
            )
        self.assertIn(good.id, valid_ids)
        self.assertIn(bad.id, valid_ids, "a malformed domain degrades to always-valid")
        self.assertTrue(any("malformed domain" in line for line in capture.output))


@tagged("post_install", "-at_install")
class TestAssociatedViewMissingActionRef(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.report = cls.env["ir.actions.report"].create(
            {
                "name": "Audit Associated View Report",
                "model": "res.partner",
                "report_name": "base.audit_associated_view_dummy",
            }
        )

    def test_returns_action_data_when_action_ref_exists(self) -> None:
        data = self.report.action_view_qweb_views()
        self.assertIsInstance(data, dict)
        matching_view, other_view = self.env["ir.ui.view"].create(
            [
                {"name": "audit_associated_view_dummy", "type": "qweb", "arch": "<t/>"},
                {"name": "audit_unrelated_view", "type": "qweb", "arch": "<t/>"},
            ]
        )
        found = self.env["ir.ui.view"].search(data["domain"])
        self.assertIn(matching_view, found)
        self.assertNotIn(other_view, found)

    def test_returns_false_when_action_ref_missing(self) -> None:
        imd = self.env["ir.model.data"].search(
            [("module", "=", "base"), ("name", "=", "action_ui_view")]
        )
        imd.unlink()
        self.assertFalse(self.report.action_view_qweb_views())

    def test_returns_false_when_report_name_has_no_module_part(self) -> None:
        self.report.report_name = "audit_no_module_part"
        self.assertFalse(self.report.action_view_qweb_views())


@tagged("post_install", "-at_install")
class TestXmlidLookupCacheOrderingAfterWrite(TransactionCase):
    def test_db_row_reflects_write_before_cache_clear(self) -> None:
        group_a = self.env["res.groups"].create({"name": "Audit Group A"})
        group_b = self.env["res.groups"].create({"name": "Audit Group B"})
        imd = self.env["ir.model.data"].create(
            {
                "module": "__test_imd_audit",
                "name": "test_group_order",
                "model": "res.groups",
                "res_id": group_a.id,
            }
        )
        self.env.flush_all()

        observed_res_id = []

        def _probe_db_on_clear_cache(*args: object, **kwargs: object) -> None:
            self.env.cr.execute(
                "SELECT res_id FROM ir_model_data WHERE module = %s AND name = %s",
                ["__test_imd_audit", "test_group_order"],
            )
            observed_res_id.append(self.env.cr.fetchone()[0])

        self.patch(self.env.registry, "clear_cache", _probe_db_on_clear_cache)
        imd.write({"res_id": group_b.id})

        self.assertTrue(observed_res_id)
        self.assertEqual(
            observed_res_id,
            [group_b.id] * len(observed_res_id),
            "the DB row must already reflect the write by the time "
            "clear_cache() runs, else a concurrent raw-SQL lookup could "
            "re-cache the pre-write row",
        )


@tagged("post_install", "-at_install")
class TestAttachmentNamesEvaluatedOnce(TransactionCase):
    def test_precomputed_names_are_not_recomputed(self):
        report = self.env["ir.actions.report"].create(
            {
                "name": "Audit attachment",
                "model": "res.partner",
                "report_name": "base.audit_attachment",
                "report_type": "qweb-pdf",
                "attachment": "'audit-%s.pdf' % object.id",
            }
        )
        records = self.env["res.partner"].search([], limit=3)
        module = "odoo.addons.base.models.ir_actions_report"
        with patch(f"{module}.safe_eval", wraps=safe_eval) as evaluated:
            filenames = report._get_attachment_filenames(records)
            baseline = evaluated.call_count
            report._get_attachments(records, filenames)
            self.assertEqual(
                evaluated.call_count,
                baseline,
                "_get_attachments recomputed the names its caller had just "
                "evaluated, doubling safe_eval over the whole batch",
            )
        self.assertEqual(len(filenames), len(records))


@tagged("post_install", "-at_install")
class TestGetReportFromName(TransactionCase):
    def test_keeps_the_caller_context_and_returns_the_sudo_report(self):
        created = self.env["ir.actions.report"].create(
            {
                "name": "Audit lookup",
                "model": "res.partner",
                "report_name": "base.audit_lookup_dummy",
            }
        )
        report = (
            self.env["ir.actions.report"]
            .with_context(audit_marker=1)
            ._get_report_from_name("base.audit_lookup_dummy")
        )
        self.assertEqual(report, created)
        self.assertTrue(report.env.su)
        self.assertEqual(report.env.context.get("audit_marker"), 1)

    def test_a_missing_or_empty_name_is_an_empty_recordset(self):
        Report = self.env["ir.actions.report"]
        self.assertFalse(Report._get_report_from_name("base.__no_such_report__"))
        self.assertFalse(Report._get_report_from_name("no_dot_no_report"))
        self.assertFalse(Report._get_report_from_name(None))
