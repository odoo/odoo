# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.controllers.form import WebsiteForm


@tagged('post_install', '-at_install')
class TestWebsiteFormEditor(HttpCaseWithUserPortal):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.email = "info@yourcompany.example.com"
        cls.env.ref("base.user_admin").write({
            'name': "Mitchell Admin",
            'phone': "+1 555-555-5555",
        })

    def test_tour(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'website_form_editor_tour', login='admin', timeout=240)
        self.start_tour('/', 'website_form_editor_tour_submit')
        self.start_tour('/', 'website_form_editor_tour_results', login="admin")

    def test_website_form_contact_us_edition_with_email(self):
        self.start_tour('/odoo', 'website_form_contactus_edition_with_email', login="admin")
        self.start_tour('/contactus', 'website_form_contactus_submit', login="portal")
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(
            mail.email_to,
            'test@test.test',
            'The email was edited, the form should have been sent to the configured email')

    def test_website_form_contact_us_edition_no_email(self):
        self.env.company.email = 'website_form_contactus_edition_no_email@mail.com'
        self.start_tour('/odoo', 'website_form_contactus_edition_no_email', login="admin")
        self.start_tour('/contactus', 'website_form_contactus_submit', login="portal")
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(
            mail.email_to,
            self.env.company.email,
            'The email was not edited, the form should still have been sent to the company email')

    def test_website_form_conditional_required_checkboxes(self):
        self.start_tour('/', 'website_form_conditional_required_checkboxes', login="admin")

    def test_contactus_form_email_stay_dynamic(self):
        # The contactus form should always be sent to the company email except
        # if the user explicitly changed it in the options.
        self.env.company.email = 'before.change@mail.com'
        self.start_tour('/contactus', 'website_form_contactus_change_random_option', login="admin")
        self.env.company.email = 'after.change@mail.com'
        self.start_tour('/contactus', 'website_form_contactus_check_changed_email', login="portal")

    def test_website_form_editable_content(self):
        self.start_tour('/', 'website_form_editable_content', login="admin")

    def test_website_form_special_characters(self):
        self.start_tour('/', 'website_form_special_characters', login='admin')
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertIn('Test1&#34;&#39;', mail.body_html, 'The single quotes and double quotes characters should be visible on the received mail')

    def test_website_form_nested_forms(self):
        self.start_tour('/my/account', 'website_form_nested_forms', login='admin')

    def test_website_form_duplicate_field_ids(self):
        self.start_tour('/', 'website_form_duplicate_field_ids', login='admin')


@tagged('post_install', '-at_install')
class TestWebsiteForm(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')])
        self.test_field = self.env['ir.model.fields'].create({
            'name': 'x_test_field',
            'model_id': self.partner_model.id,
            'ttype': 'char',
            'field_description': 'test',
        })

    def test_website_form_html_escaping(self):
        website = self.env['website'].browse(1)
        WebsiteFormController = WebsiteForm()
        with MockRequest(self.env, website=website):
            WebsiteFormController.insert_record(
                request,
                self.env['ir.model'].search([('model', '=', 'mail.mail')]),
                {'email_from': 'odoobot@example.com', 'subject': 'John <b>Smith</b>', 'email_to': 'company@company.company'},
                "John <b>Smith</b>",
            )
            mail = self.env['mail.mail'].search([], order='id desc', limit=1)
            self.assertNotIn('<b>', mail.body_html, "HTML should be escaped in website form")
            self.assertIn('&lt;b&gt;', mail.body_html, "HTML should be escaped in website form (2)")

    def test_website_form_commit_when_creating(self):
        self.env.ref('base.model_res_partner').website_form_access = True
        self.env['ir.model.fields'].formbuilder_whitelist('res.partner', ['name'])
        WebsiteFormController = WebsiteForm()
        original_insert_record = WebsiteFormController.insert_record
        test_sp = self.env.cr.savepoint()
        def dummy_insert_record(*args, **kwargs):
            res = original_insert_record(*args, **kwargs)
            # delete website_form savepoint by rollbacking to test savepoint
            self.env.cr.execute('ROLLBACK TO SAVEPOINT "%s"' % test_sp.name)
            return res
        WebsiteFormController.insert_record = dummy_insert_record
        with MockRequest(self.env):
            request.params = {
                'model_name': 'res.partner',
                'name': 'test partner',
            }
            with self.assertLogs(level='ERROR'):
                response = WebsiteFormController.website_form(
                    **request.params,
                )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data.startswith(b'{"id":'))
        test_sp.close(rollback=True)

    def test_cannot_delete_field_used_in_website_form(self):
        """
        Test that deleting a field used in a website form raises a ValidationError.
        """
        self.env['ir.ui.view'].create({
            'name': 'Test Form for Deletion Constraint',
            'type': 'qweb',
            'arch_db': f'''
                <template id="test_form_template_for_deletion">
                    <form action="/website/form/" data-model_name="res.partner">
                        <label for="my_input">Test Input</label>
                        <input type="text" name="{self.test_field.name}" id="my_input"/>
                        <button type="submit">Submit</button>
                    </form>
                </template>
            ''',
        })
        with self.assertRaises(ValidationError):
            self.test_field.unlink()
        self.assertTrue(self.test_field.exists())
