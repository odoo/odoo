# Copyright 2017 Tecnativa - Pedro M. Baeza
# Copyright 2020 Onestein - Andrea Stirpe
# Copyright 2021 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from werkzeug.urls import url_join

from odoo import _
from odoo.tests import common, tagged


@tagged("-at_install", "post_install")
class TestMailDebrandDigest(common.TransactionCase):
    def setUp(self):
        super().setUp()
        if "digest.digest" in self.env:
            self.mail_digest_id = self.env["digest.digest"].create(
                {
                    "name": "Test Digest",
                    "user_ids": False,
                    "company_id": self.env.company.id,
                    "kpi_res_users_connected": True,
                    "kpi_mail_message_total": True,
                }
            )
        else:
            self.mail_digest_id = False

    def test_mail_digest(self):
        if not self.mail_digest_id:
            self.assertEqual(True, True)
            return

        web_base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        rendered_body = self.env["mail.render.mixin"]._render_template(
            "digest.digest_mail_main",
            "digest.digest",
            self.mail_digest_id.ids,
            engine="qweb",
            add_context={
                "title": self.mail_digest_id.name,
                "top_button_label": _("Connect"),
                "top_button_url": url_join(web_base_url, "/web/login"),
                "company": self.env.user.company_id,
                "user": self.env.user,
                "tips_count": 1,
                "formatted_date": datetime.today().strftime("%B %d, %Y"),
                "display_mobile_banner": True,
                "kpi_data": self.mail_digest_id.compute_kpis(
                    self.env.user.company_id, self.env.user
                ),
                "tips": self.mail_digest_id.compute_tips(
                    self.env.user.company_id, self.env.user, tips_count=1, consumed=True
                ),
                "preferences": self.mail_digest_id.compute_preferences(
                    self.env.user.company_id, self.env.user
                ),
            },
            post_process=True,
        )[self.mail_digest_id.id]

        # ensure the template rendered correctly. if rendering failed,
        # we sometimes end up with a string only containing the template
        # name, or a null-ish value
        self.assertNotEqual(rendered_body, "digest.digest_mail_main")
        self.assertNotEqual(rendered_body, None)
        self.assertNotEqual(rendered_body, False)
        self.assertNotEqual(rendered_body, "")
