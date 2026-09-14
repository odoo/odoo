from unittest.mock import patch

import odoo.tests
from odoo.exceptions import AccessError, UserError
from odoo.http import root
from odoo.tools import mute_logger

from odoo.addons.http_routing.tests.common import MockRequest


@odoo.tests.tagged("web_http", "web_report")
class TestReports(odoo.tests.HttpCase):
    def test_report_session_cookie(self):
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
        origin_get_record = self.env.registry["ir.binary"]._get_record

        def _get_record(
            self,
            xmlid=None,
            res_model="ir.attachment",
            res_id=None,
            access_token=None,
            field_name=None,
        ):
            if res_model == "ir.attachment" and res_id == image.id:
                result["uid"] = self.env.uid
                record = origin_get_record(
                    self, xmlid, res_model, res_id, access_token, field_name
                )
                result.update({"record_id": record.id, "data": record.datas})
            else:
                record = origin_get_record(
                    self, xmlid, res_model, res_id, access_token, field_name
                )
            return record

        self.patch(self.env.registry["ir.binary"], "_get_record", _get_record)

        admin = self.env.ref("base.user_admin")
        admin_device_log_count_before = self.env["res.device.log"].search_count(
            [("user_id", "=", admin.id)]
        )
        report = report.with_user(admin)
        with MockRequest(report.env, is_frontend=False) as mock_request:
            mock_request.session = self.authenticate(admin.login, admin.login)
            report.with_context(force_report_rendering=True)._render_qweb_pdf(
                report.id, [partner_id]
            )
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

        self.logout()
        result.clear()
        public = self.env.ref("base.public_user")
        public_device_log_count_before = self.env["res.device.log"].search_count(
            [("user_id", "=", public.id)]
        )
        # The records bound the print (bfdd12837e3c): a user who may not read
        # the partner is refused before the PDF engine is asked for anything,
        # so nothing is fetched as anyone and no device is logged in.
        report = report.with_user(public)
        with MockRequest(self.env, is_frontend=False) as mock_request:
            mock_request.session = self.authenticate(None, None)
            with self.assertRaises(AccessError):
                report.with_context(force_report_rendering=True)._render_qweb_pdf(
                    report.id, [partner_id]
                )
        public_device_log_count_after = self.env["res.device.log"].search_count(
            [("user_id", "=", public.id)]
        )
        self.assertFalse(public_device_log_count_after - public_device_log_count_before)
        self.assertEqual(
            result,
            {},
            "PDF engine must not have been asked to fetch anything for a print "
            "the caller may not make",
        )

    @mute_logger("odoo.addons.web.models.ir_actions_report")
    def test_report_error_cleanup(self):
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
            MockRequest(report.env, is_frontend=False) as mock_request,
            patch("weasyprint.HTML") as mock_weasyprint,
            patch.object(root.session_store, "delete") as mock_delete,
        ):
            mock_request.session = self.authenticate(admin.login, admin.login)

            mock_weasyprint.return_value.render.side_effect = Exception(
                "rendering failed"
            )

            with self.assertRaises(UserError):
                report.with_context(force_report_rendering=True)._render_qweb_pdf(
                    report.id
                )

            self.assertEqual(mock_delete.call_count, 1)
            self.assertNotEqual(
                mock_delete.call_args.args[0].sid, mock_request.session.sid
            )
