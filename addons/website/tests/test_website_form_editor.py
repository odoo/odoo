from odoo import SUPERUSER_ID, Command
from odoo.exceptions import AccessDenied, AccessError, ValidationError
from odoo.http import request
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import hmac

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.controllers.form import WebsiteForm


@tagged("post_install", "-at_install")
class TestWebsiteFormEditor(HttpCaseWithUserPortal):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.email = "info@yourcompany.example.com"
        cls.env.ref("base.user_admin").write(
            {
                "name": "Mitchell Admin",
                "phone_ids": [
                    Command.create({"number": "+1 555-555-5555", "type": "landline"})
                ],
            }
        )

    def test_tour(self):
        self.start_tour(
            self.env["website"].get_client_action_url("/"),
            "website_form_editor_tour",
            login="admin",
            timeout=240,
        )
        self.start_tour("/", "website_form_editor_tour_submit")
        self.start_tour("/", "website_form_editor_tour_results", login="admin")

    def test_website_form_contact_us_edition_with_email(self):
        self.start_tour(
            "/odoo", "website_form_contactus_edition_with_email", login="admin"
        )
        self.start_tour("/contactus", "website_form_contactus_submit", login="portal")
        mail = self.env["mail.mail"].search([], order="id desc", limit=1)
        self.assertEqual(
            mail.email_to,
            "test@test.test",
            "The email was edited, the form should have been sent to the configured email",
        )

    def test_website_form_contact_us_edition_no_email(self):
        self.env.company.email = "website_form_contactus_edition_no_email@mail.com"
        self.start_tour(
            "/odoo", "website_form_contactus_edition_no_email", login="admin"
        )
        self.start_tour("/contactus", "website_form_contactus_submit", login="portal")
        mail = self.env["mail.mail"].search([], order="id desc", limit=1)
        self.assertEqual(
            mail.email_to,
            self.env.company.email,
            "The email was not edited, the form should still have been sent to the company email",
        )

    def test_website_form_conditional_required_checkboxes(self):
        self.start_tour(
            "/", "website_form_conditional_required_checkboxes", login="admin"
        )

    def test_contactus_form_email_stay_dynamic(self):
        self.env.company.email = "before.change@mail.com"
        self.start_tour(
            "/contactus", "website_form_contactus_change_random_option", login="admin"
        )
        self.env.company.email = "after.change@mail.com"
        self.start_tour(
            "/contactus", "website_form_contactus_check_changed_email", login="portal"
        )

    def test_website_form_editable_content(self):
        self.start_tour("/", "website_form_editable_content", login="admin")

    def test_website_form_special_characters(self):
        self.start_tour("/", "website_form_special_characters", login="admin")
        mail = self.env["mail.mail"].search([], order="id desc", limit=1)
        self.assertIn(
            "Test1&#34;&#39;",
            mail.body_html,
            "The single quotes and double quotes characters should be visible on the received mail",
        )

    def test_website_form_nested_forms(self):
        self.start_tour("/my/account", "website_form_nested_forms", login="admin")

    def test_website_form_duplicate_field_ids(self):
        self.start_tour("/", "website_form_duplicate_field_ids", login="admin")


@tagged("post_install", "-at_install")
class TestWebsiteForm(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner_model = self.env["ir.model"].search(
            [("model", "=", "res.partner")]
        )
        self.test_field = self.env["ir.model.fields"].create(
            {
                "name": "x_test_field",
                "model_id": self.partner_model.id,
                "ttype": "char",
                "field_description": "test",
            }
        )

    def test_website_form_html_escaping(self):
        website = self.env["website"].browse(1)
        WebsiteFormController = WebsiteForm()
        with MockRequest(self.env, website=website):
            WebsiteFormController.create_record(
                request,
                self.env["ir.model"].search([("model", "=", "mail.mail")]),
                {
                    "email_from": "odoobot@example.com",
                    "subject": "John <b>Smith</b>",
                    "email_to": "company@company.company",
                },
                "John <b>Smith</b>",
            )
            mail = self.env["mail.mail"].search([], order="id desc", limit=1)
            self.assertNotIn(
                "<b>", mail.body_html, "HTML should be escaped in website form"
            )
            self.assertIn(
                "&lt;b&gt;",
                mail.body_html,
                "HTML should be escaped in website form (2)",
            )

    def test_form_non_mail_field_whitelist(self):
        partner_model = self.env["ir.model"].search([("model", "=", "res.partner")])
        partner_model.website_form_access = True
        self.env["ir.model.fields"].formbuilder_whitelist("res.partner", ["name"])
        controller = WebsiteForm()
        website = self.env["website"].browse(1)
        with MockRequest(self.env, website=website):
            data = controller.extract_data(
                partner_model.sudo(),
                {
                    "name": "Legit Name",
                    "function": "injected",
                    "website_published": "1",
                },
            )
        self.assertEqual(data["record"].get("name"), "Legit Name")
        self.assertNotIn(
            "function",
            data["record"],
            "a non-whitelisted field must not reach the record",
        )
        self.assertNotIn(
            "website_published",
            data["record"],
            "a non-whitelisted field must not reach the record",
        )
        self.assertIn(
            "function",
            data["custom"],
            "non-whitelisted fields are routed to the custom dump",
        )

    def test_website_form_commit_when_creating(self):
        self.env.ref("base.model_res_partner").website_form_access = True
        self.env["ir.model.fields"].formbuilder_whitelist("res.partner", ["name"])
        WebsiteFormController = WebsiteForm()
        original_insert_record = WebsiteFormController.create_record
        test_sp = self.env.cr.savepoint()

        def dummy_insert_record(*args, **kwargs):
            res = original_insert_record(*args, **kwargs)
            self.env.cr.execute('ROLLBACK TO SAVEPOINT "%s"' % test_sp.name)
            return res

        WebsiteFormController.create_record = dummy_insert_record
        with MockRequest(self.env):
            request.params = {
                "model_name": "res.partner",
                "name": "test partner",
            }
            with self.assertLogs(level="ERROR"):
                response = WebsiteFormController.website_form(
                    **request.params,
                )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data.startswith(b'{"id":'))
        test_sp.close(rollback=True)

    def test_cannot_delete_field_used_in_website_form(self):
        self.env["ir.ui.view"].create(
            {
                "name": "Test Form for Deletion Constraint",
                "type": "qweb",
                "arch_db": f'''
                <template id="test_form_template_for_deletion">
                    <form action="/website/form/" data-model_name="res.partner">
                        <label for="my_input">Test Input</label>
                        <input type="text" name="{self.test_field.name}" id="my_input"/>
                        <button type="submit">Submit</button>
                    </form>
                </template>
            ''',
            }
        )
        with self.assertRaises(ValidationError):
            self.test_field.unlink()
        self.assertTrue(self.test_field.exists())

    def test_delete_field_scans_malformed_html_without_crashing(self):
        malformed = (
            "<p>Contact &amp; win</p>"
            f'<form data-model_name="res.partner"><input name="{self.test_field.name}"><br></form>'
        )
        self.env["website.menu"].create(
            {
                "name": "Mega",
                "url": "#",
                "mega_menu_content": malformed,
            }
        )

        other = self.env["ir.model.fields"].create(
            {
                "name": "x_unrelated_field",
                "model_id": self.partner_model.id,
                "ttype": "char",
                "field_description": "unrelated",
            }
        )
        other.unlink()
        self.assertFalse(other.exists())

        with self.assertRaises(ValidationError):
            self.test_field.unlink()
        self.assertTrue(self.test_field.exists())

    def test_mail_form_signature_is_mandatory(self):
        website = self.env["website"].browse(1)
        self.env["ir.model"].search(
            [("model", "=", "mail.mail")]
        ).website_form_access = True
        controller = WebsiteForm()
        before = self.env["mail.mail"].search_count([])

        with MockRequest(self.env, website=website):
            with self.assertRaises(AccessDenied):
                controller._handle_website_form(
                    "mail.mail",
                    email_from="attacker@evil.example",
                    email_cc="victim1@example.com,victim2@example.com",
                    subject="spam",
                    body="spam",
                    website_form_signature="not-a-valid-signature",
                )
            with self.assertRaises(AccessDenied):
                controller._handle_website_form(
                    "mail.mail",
                    email_from="attacker@evil.example",
                    email_cc="victim@example.com",
                    subject="spam",
                    body="spam",
                )
            good_to = "company@company.example"
            good_sig = hmac(self.env, "website_form_signature", good_to)
            with self.assertRaises(AccessDenied):
                controller._handle_website_form(
                    "mail.mail",
                    email_from="visitor@example.com",
                    email_to="attacker@evil.example",
                    subject="hello",
                    body="hello",
                    website_form_signature=good_sig,
                )

        self.assertEqual(self.env["mail.mail"].search_count([]), before)

        with MockRequest(self.env, website=website):
            controller._handle_website_form(
                "mail.mail",
                email_from="visitor@example.com",
                email_to=good_to,
                subject="hello",
                body="hello",
                website_form_signature=good_sig,
            )
        self.assertEqual(
            self.env["mail.mail"].search_count([]),
            before + 1,
            "A validly signed submission should create the mail.",
        )

    def test_get_authorized_fields_requires_editor(self):
        IrModel = self.env["ir.model"]
        public = self.env.ref("base.public_user")
        with self.assertRaises(AccessError):
            IrModel.with_user(public).get_fields_authorized("res.partner", {})

        self.env.ref("base.model_res_partner").website_form_access = True
        fields = IrModel.with_user(SUPERUSER_ID).get_fields_authorized(
            "res.partner", {}
        )
        self.assertIn("name", fields)

    def test_get_authorized_fields_requires_form_access(self):
        IrModel = self.env["ir.model"]
        with self.assertRaises(AccessError):
            IrModel.with_user(SUPERUSER_ID).get_fields_authorized("res.country", {})

    def test_mail_form_signature_binds_cc_recipients(self):
        from odoo.addons.website.tools import website_form_signature_payload

        website = self.env["website"].browse(1)
        self.env["ir.model"].search(
            [("model", "=", "mail.mail")]
        ).website_form_access = True
        controller = WebsiteForm()
        good_to = "company@company.example"
        before = self.env["mail.mail"].search_count([])

        with MockRequest(self.env, website=website):
            sig_no_cc = hmac(
                self.env,
                "website_form_signature",
                website_form_signature_payload(good_to, {}),
            )
            with self.assertRaises(AccessDenied):
                controller._handle_website_form(
                    "mail.mail",
                    email_to=good_to,
                    email_cc="victim@evil.example",
                    subject="spam",
                    body="spam",
                    website_form_signature=sig_no_cc,
                )
            sig_copy = hmac(
                self.env,
                "website_form_signature",
                website_form_signature_payload(
                    good_to, {"email_cc": "copy@company.example"}
                ),
            )
            with self.assertRaises(AccessDenied):
                controller._handle_website_form(
                    "mail.mail",
                    email_to=good_to,
                    email_cc="victim@evil.example",
                    subject="spam",
                    body="spam",
                    website_form_signature=sig_copy,
                )

        self.assertEqual(
            self.env["mail.mail"].search_count([]),
            before,
            "No relay mail must be created by a rejected Cc injection.",
        )

        with MockRequest(self.env, website=website):
            sig_copy = hmac(
                self.env,
                "website_form_signature",
                website_form_signature_payload(
                    good_to, {"email_cc": "copy@company.example"}
                ),
            )
            controller._handle_website_form(
                "mail.mail",
                email_to=good_to,
                email_cc="copy@company.example",
                subject="hello",
                body="hello",
                website_form_signature=sig_copy,
            )
        self.assertEqual(self.env["mail.mail"].search_count([]), before + 1)
