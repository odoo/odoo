from unittest.mock import patch

import odoo.tests
from odoo.exceptions import UserError
from odoo.http import root
from odoo.tools import mute_logger

from odoo.addons.base.models.ir_actions_report import _weasy_image_cache
from odoo.addons.http_routing.tests.common import MockRequest


@odoo.tests.tagged("web_http", "web_report")
class TestReports(odoo.tests.HttpCase):
    def test_report_session_cookie(self):
        """Asserts the PDF engine forwards the user session when requesting resources from Odoo, such as images,
        and that the resource is correctly returned as expected.
        """
        partner_id = self.env.user.partner_id.id
        img = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
        image = self.env["ir.attachment"].create(
            {
                "name": "foo",
                "res_model": "res.partner",
                "res_id": partner_id,
                "datas": img,
            }
        )
        report = self.env["ir.actions.report"].create(
            {
                "name": "test report",
                "report_name": "base.test_report",
                "model": "res.partner",
            }
        )
        self.env["ir.ui.view"].create(
            {
                "type": "qweb",
                "name": "base.test_report",
                "key": "base.test_report",
                "arch": f"""
                <main>
                    <div class="article" data-oe-model="res.partner" t-att-data-oe-id="docs.id">
                        <img src="/web/image/{image.id}"/>
                    </div>
                </main>
            """,
            }
        )

        result = {}
        origin_find_record = self.env.registry["ir.binary"]._find_record

        def _find_record(
            self,
            xmlid=None,
            res_model="ir.attachment",
            res_id=None,
            access_token=None,
            field=None,
        ):
            if res_model == "ir.attachment" and res_id == image.id:
                result["uid"] = self.env.uid
                record = origin_find_record(
                    self, xmlid, res_model, res_id, access_token, field
                )
                result.update({"record_id": record.id, "data": record.datas})
            else:
                record = origin_find_record(
                    self, xmlid, res_model, res_id, access_token, field
                )
            return record

        self.patch(self.env.registry["ir.binary"], "_find_record", _find_record)

        # 1. Request the report as admin, who has access to the image
        admin = self.env.ref("base.user_admin")
        admin_device_log_count_before = self.env["res.device.log"].search_count(
            [("user_id", "=", admin.id)]
        )
        report = report.with_user(admin)
        with MockRequest(report.env) as mock_request:
            mock_request.session = self.authenticate(admin.login, admin.login)
            report.with_context(force_report_rendering=True)._render_qweb_pdf(
                report.id, [partner_id]
            )
        # Check that no device logs have been generated
        admin_device_log_count_after = self.env["res.device.log"].search_count(
            [("user_id", "=", admin.id)]
        )
        self.assertFalse(admin_device_log_count_after - admin_device_log_count_before)

        self.assertEqual(
            result.get("uid"),
            admin.id,
            "PDF engine is not fetching the image as the user printing the report",
        )
        self.assertEqual(
            result.get("record_id"),
            image.id,
            "PDF engine did not fetch the expected record",
        )
        self.assertEqual(
            result.get("data"),
            img,
            "PDF engine did not fetch the right image content",
        )

        # 2. Request the report as public, who has no access to the image
        self.logout()
        result.clear()
        # Clear WeasyPrint's shared image cache so the second render
        # actually fetches the image (instead of reusing the cached copy
        # from the admin render above).
        _weasy_image_cache.clear()
        public = self.env.ref("base.public_user")
        public_device_log_count_before = self.env["res.device.log"].search_count(
            [("user_id", "=", public.id)]
        )
        report = report.with_user(public)
        with MockRequest(self.env) as mock_request:
            mock_request.session = self.authenticate(None, None)
            report.with_context(force_report_rendering=True)._render_qweb_pdf(
                report.id, [partner_id]
            )
        # Check that no device logs have been generated
        public_device_log_count_after = self.env["res.device.log"].search_count(
            [("user_id", "=", public.id)]
        )
        self.assertFalse(public_device_log_count_after - public_device_log_count_before)

        self.assertEqual(
            result.get("uid"),
            public.id,
            "PDF engine is not fetching the image as the user printing the report",
        )
        self.assertEqual(
            result.get("record_id"),
            None,
            "PDF engine must not have been allowed to fetch the image",
        )
        self.assertEqual(
            result.get("data"),
            None,
            "PDF engine must not have been allowed to fetch the image",
        )

    @mute_logger("odoo.addons.base.models.ir_actions_report")
    def test_report_error_cleanup(self):
        """Asserts the temporary session created for the PDF URL fetcher is
        cleaned up even when rendering fails."""
        admin = self.env.ref("base.user_admin")
        self.env["ir.ui.view"].create(
            {
                "type": "qweb",
                "name": "base.test_report",
                "key": "base.test_report",
                "arch": """
                <main>
                    <div class="article" data-oe-model="res.partner" data-oe-id="1">
                        <p>TEST</p>
                    </div>
                </main>
            """,
            }
        )
        report = self.env["ir.actions.report"].create(
            {
                "name": "test report",
                "report_name": "base.test_report",
                "model": "res.partner",
            }
        )
        report = report.with_user(admin)

        with (
            MockRequest(report.env) as mock_request,
            patch("weasyprint.HTML") as mock_weasyprint,
            patch.object(root.session_store, "delete") as mock_delete,
        ):
            mock_request.session = self.authenticate(admin.login, admin.login)

            # Simulate a WeasyPrint rendering failure
            mock_weasyprint.return_value.write_pdf.side_effect = Exception(
                "rendering failed"
            )

            with self.assertRaises(UserError):
                report.with_context(force_report_rendering=True)._render_qweb_pdf(
                    report.id
                )

            # Check that the temporary session has been deleted (not the user's session)
            self.assertEqual(mock_delete.call_count, 1)
            self.assertNotEqual(
                mock_delete.call_args.args[0].sid, mock_request.session.sid
            )
