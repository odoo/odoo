# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, ValidationError
from odoo.http import request
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.addons.website.tools import MockRequest


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

    def test_website_form_server_errors(self):
        self.browser_js('/contactus', r"""
            const publicWidget = odoo.loader.modules.get(
                '@web/legacy/js/public/public_widget'
            )[Symbol.for('default')];
            const form = document.createElement('form');
            form.innerHTML = `
                <div class="s_website_form_field">
                    <label class="col-form-label" for="generated-team-id">Team</label>
                    <input id="generated-team-id" name="team_id" type="text"
                           class="s_website_form_input form-control" value="invalid"/>
                </div>
                <div class="s_website_form_field">
                    <input name="subject" class="s_website_form_input form-control" value="Test"/>
                </div>
                <div class="s_website_form_field">
                    <label class="col-form-label" for="generated-choice-id">Choice</label>
                    <input id="generated-choice-id" name="choice" type="radio" value="a"
                           class="s_website_form_input form-check-input" checked="checked"/>
                    <input name="choice" type="radio" value="b"
                           class="s_website_form_input form-check-input"/>
                </div>`;
            document.body.appendChild(form);
            const checkErrors = publicWidget.registry.s_website_form.prototype.check_error_fields.bind({
                $el: $(form),
            });
            const assert = (condition, message) => {
                if (!condition) {
                    throw new Error(message);
                }
            };
            const team = form.querySelector('[name="team_id"]');
            const subject = form.querySelector('[name="subject"]');
            assert(!checkErrors(['team_id']), 'Server error lists must invalidate the form');
            assert(team.classList.contains('is-invalid'), 'Match the input name, not its generated ID');
            assert(team.closest('.s_website_form_field').classList.contains('o_has_error'),
                   'Highlight the rejected field');
            assert(!subject.classList.contains('is-invalid'), 'Other fields must remain valid');
            assert(checkErrors({}), 'The form must be valid after clearing server errors');
            assert(!team.classList.contains('is-invalid'), 'Clear the previous highlighting');
            assert(!checkErrors({subject: true}), 'Continue accepting error mappings');
            assert(subject.classList.contains('is-invalid'), 'Fields without labels must be matched');
            assert(!checkErrors(['choice']), 'Recognize server errors for radio groups');
            assert([...form.querySelectorAll('[name="choice"]')].every(
                input => input.classList.contains('is-invalid')
            ), 'Highlight all inputs in the rejected group');
            assert(!checkErrors({team_id: 'Invalid team'}), 'Continue accepting field error messages');
            assert(document.querySelector('.popover-body').textContent === 'Invalid team',
                   'Display the server error message');
            $(team.closest('.s_website_form_field')).popover('dispose');
            team.required = true;
            team.value = '';
            assert(!checkErrors({}), 'Browser validation must still reject required empty inputs');
            assert(team.classList.contains('is-invalid'), 'Highlight browser-invalid inputs');
            form.remove();
            console.log('test successful');
        """, ready="odoo.loader.modules.has('@website/snippets/s_website_form/000')")


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
        def dummy_insert_record(*args, **kwargs):
            res = original_insert_record(*args, **kwargs)
            # delete website_form savepoint by rollbacking to test savepoint
            self.env.cr.execute('ROLLBACK TO SAVEPOINT test_%d' % self._savepoint_id)
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

    def test_can_delete_field_when_no_access_other_field(self):
        """
        Tests that a user without access to an html field checked by the website form delete hook can still delete other fields
        """
        self.test_field_2 = self.env['ir.model.fields'].create({
            'name': 'x_test_field_2',
            'model_id': self.partner_model.id,
            'ttype': 'html',
            'field_description': 'test2',
            'sanitize': False,
        })
        user = self.env['res.users'].create({
            'name': 'A User',
            'login': 'a_user',
            'email': 'a@user.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_system').id])],
        })
        self.env['ir.model.access'].search([('model_id', '=', self.partner_model.id)]).perm_read = False
        with self.with_user(user.login):
            with self.assertRaises(AccessError):
                self.env['res.partner'].search([])
            activity_model = self.env['ir.model'].search([('model', '=', 'mail.activity')])
            other_test_field = self.env['ir.model.fields'].create({
                'name': 'x_test_field',
                'model_id': activity_model.id,
                'ttype': 'char',
                'field_description': 'test',
            })
            other_test_field.unlink()
            self.assertFalse(other_test_field.exists())
