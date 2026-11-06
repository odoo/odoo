# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from lxml import html

from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.http import request
from odoo.tests.common import HttpCase, TransactionCase, tagged

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
        self.start_tour(self.env['website'].get_client_action_url('/', True), 'website_form_editor_tour', login='admin', timeout=240)
        self.start_tour('/', 'website_form_editor_tour_submit')
        self.start_tour('/', 'website_form_editor_tour_results', login="admin")

    def test_website_form_contact_us_edition_with_email(self):
        self.start_tour(self.env['website'].get_client_action_url('/contactus', True), 'website_form_contactus_edition_with_email', login="admin")
        self.start_tour('/contactus', 'website_form_contactus_submit', login="portal")
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(
            mail.email_to,
            'test@test.test',
            'The email was edited, the form should have been sent to the configured email')

    def test_website_form_contact_us_edition_no_email(self):
        self.env.company.email = 'website_form_contactus_edition_no_email@mail.com'
        self.start_tour(self.env['website'].get_client_action_url('/contactus', True), 'website_form_contactus_edition_no_email', login="admin")
        self.start_tour('/contactus', 'website_form_contactus_submit', login="portal")
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(
            mail.email_to,
            self.env.company.email,
            'The email was not edited, the form should still have been sent to the company email')

    def test_website_form_conditional_required_checkboxes(self):
        self.start_tour(self.env['website'].get_client_action_url('/', True), 'website_form_conditional_required_checkboxes', login="admin")

    def test_contactus_form_email_stay_dynamic(self):
        # The contactus form should always be sent to the company email except
        # if the user explicitly changed it in the options.
        self.env.company.email = 'before.change@mail.com'
        self.start_tour(self.env['website'].get_client_action_url('/contactus', True), 'website_form_contactus_change_random_option', login="admin")
        self.env.company.email = 'after.change@mail.com'
        self.start_tour('/contactus', 'website_form_contactus_check_changed_email', login="portal")

    def test_website_form_editable_content(self):
        self.start_tour(self.env['website'].get_client_action_url('/', True), 'website_form_editable_content', login="admin")

    def test_website_form_special_characters(self):
        self.start_tour(self.env['website'].get_client_action_url('/', True), 'website_form_special_characters', login='admin')
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertIn('Test1&#34;&#39;', mail.body_html, 'The single quotes and double quotes characters should be visible on the received mail')

    def test_website_form_nested_forms(self):
        self.start_tour(self.env["website"].get_client_action_url('/my/account', True), 'website_form_nested_forms', login='admin')

    def test_website_form_duplicate_field_ids(self):
        self.start_tour(self.env["website"].get_client_action_url('/', True), 'website_form_duplicate_field_ids', login='admin')


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
        website = self.env.ref('base.default_website')
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

        with (
            self.enter_registry_test_mode(),
            self.env.registry.cursor() as test_cr,
            MockRequest(self.env(cr=test_cr)),
        ):
            def dummy_insert_record(*args, **kwargs):
                res = original_insert_record(*args, **kwargs)
                test_cr.commit()
                return res
            WebsiteFormController.insert_record = dummy_insert_record
            WebsiteFormController._verify_website_form = lambda model_name, values: None
            request.params = {
                'model_name': 'res.partner',
                'name': 'test partner',
            }
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
            'group_ids': [(6, 0, [self.env.ref('base.group_system').id])],
        })
        self.env['ir.access'].create({
            'name': 'Read Restriction',
            'model_id': self.partner_model.id,
            'operation': 'r',
            'domain': Domain.FALSE
        })
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

    def test_reference_field_not_offered_in_form_builder(self):
        """
        Reference-type fields have no input template in the website form
        builder, so they must not appear in the field list it offers
        """
        self.env["ir.model.fields"].create(
            {
                "name": "x_test_website_form_ref",
                "field_description": "Test Reference",
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "ttype": "reference",
                "selection_ids": [(0, 0, {"value": "res.partner", "name": "Contact"})],
            },
        )

        authorized_fields = self.env["ir.model"].get_authorized_fields(
            "res.partner",
            [],
        )
        self.assertNotIn(
            "x_test_website_form_ref",
            authorized_fields,
            "Reference fields must not be offered in the website form builder.",
        )


@tagged('post_install', '-at_install')
class TestWebsiteFormSignature(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.model_res_partner').website_form_access = True
        cls.env['ir.model.fields'].formbuilder_whitelist('res.partner', ['name', 'function', 'ref', 'street', 'city', 'zip', 'website', 'email'])
        view = cls.env['ir.ui.view'].create({
            'name': 'Form',
            'type': 'qweb',
            'arch': """
                <t t-call="website.layout">
                    <span data-for="test_form" t-att-data-values="{'function': 'Manager'}"/>
                    <form id="test_form" action="/website/form/" data-model_name="res.partner">
                        <input class="s_website_form_input" name="name" required="1"/>
                        <select class="s_website_form_input" name="Department">
                            <option value="Sales"/>
                            <option>Support</option>
                        </select>
                        <select class="s_website_form_input" name="Country">
                            <option value=""/>
                        </select>
                        <select class="s_website_form_input" name="country_id">
                            <option value=""/>
                            <option value="1">Belgium</option>
                            <option value="2">Singapore</option>
                        </select>
                        <!-- Disabled by its script when it has no state of the selected country -->
                        <select class="s_website_form_input" name="state_id" required="1" data-link-state-to-country="true">
                            <option value=""/>
                            <option value="10" data-country-id="1">Brussels</option>
                        </select>
                        <input type="checkbox" class="s_website_form_input" name="Topics" value="Price, quote"/>
                        <input type="checkbox" class="s_website_form_input" name="Topics" value="Delivery"/>
                        <div class="s_website_form_field" data-visibility-dependency="Department"
                            data-visibility-comparator="selected" data-visibility-condition="Support">
                            <input class="s_website_form_input" name="street"/>
                        </div>
                        <div class="s_website_form_field" data-visibility-dependency="Topics"
                            data-visibility-comparator="contains" data-visibility-condition='["Price, quote"]'>
                            <input class="s_website_form_input" name="city"/>
                        </div>
                        <div class="s_website_form_field" data-visibility-dependency="name" data-visibility-comparator="contains">
                            <input class="s_website_form_input" name="zip"/>
                        </div>
                        <div class="s_website_form_field s_website_form_field_hidden">
                            <input class="s_website_form_input" name="website" value="https://www.odoo.com"/>
                        </div>
                        <input type="hidden" class="s_website_form_input" name="function"/>
                        <input type="hidden" class="s_website_form_input" name="ref" value="WEB"/>
                        <div class="s_website_form_field" data-requirement-comparator="substring"
                            data-requirement-condition='[{"requirement_text": "Odoo"}]'>
                            <textarea class="s_website_form_input" name="Message" minlength="5" maxlength="10"/>
                        </div>
                        <input type="email" class="s_website_form_input" name="email"/>
                        <div class="s_website_form_field" data-requirement-comparator="greater" data-requirement-condition="17">
                            <input type="number" class="s_website_form_input" name="Age" step="1"/>
                        </div>
                        <div class="s_website_form_field" data-requirement-comparator="after" data-requirement-condition="today">
                            <input class="s_website_form_input" name="Date"/>
                        </div>
                        <div class="s_website_form_field s_website_form_custom s_website_form_field_hidden">
                            <div class="s_website_form_date">
                                <input class="s_website_form_input" name="Birthday" value="1700000000"/>
                            </div>
                        </div>
                        <input type="file" class="s_website_form_input" name="Photo [image]" accept="image/*" data-max-file-size="1"/>
                    </form>
                </t>
            """,
        })
        cls.env['website.page'].create({'url': '/test-form-signature', 'view_id': view.id, 'is_published': True})

    def submit(self, values, model_name='res.partner', files=None):
        page = html.fromstring(self.url_open('/test-form-signature').content)
        signature = page.xpath('//form[@id="test_form"]/input[@name="website_form_signature"]/@value')[0]
        return self.url_open(f'/website/form/{model_name}', data={'website_form_signature': signature, **values}, files=files).json()

    def test_submit_signed_form(self):
        result = self.submit({
            'name': 'Demo',
            'Department': 'Sales',
            'Topics': 'Price, quote,Delivery',
            'Country': 'Belgium',  # an option loaded in the browser
            'country_id': '2',  # without state
            'street': 'Street of a hidden field',
            'city': 'Brussels',
            'zip': '1000',  # visible, as its rule has no condition
            'function': 'Forged',
            'ref': 'Forged',
            'website': 'https://forged.com',
            'Message': 'Odoo\r\nrocks',  # 10 characters, as counted by the browsers
            'email': "o'brien@example.com",
            'Age': '18',
            'Date': (date.today() + timedelta(days=2)).strftime('%m/%d/%Y'),
            'Birthday': '01/01/2000',
        }, files={'Photo [image][0][0]': ('photo.png', b'photo', 'image/png')})
        partner = self.env['res.partner'].browse(result['id'])
        self.assertRecordValues(partner, [{
            'name': 'Demo',
            'street': False,
            'city': 'Brussels',
            'zip': '1000',
            'function': 'Manager',
            'ref': 'WEB',
            'website': 'https://www.odoo.com',
            'email': "o'brien@example.com",
        }])
        # The default date of the hidden field, as displayed by its date picker
        self.assertIn('Birthday : 11/14/2023', ''.join(partner.message_ids.mapped('body')))
        result = self.submit({'name': 'Demo', 'Department': 'Support', 'street': 'Street', 'city': 'Brussels', 'state_id': '10'})
        self.assertRecordValues(self.env['res.partner'].browse(result['id']), [{'street': 'Street', 'city': False}])

    def test_submit_forged_form(self):
        # Check form submission without signature.
        self.assertIn('error', self.url_open('/website/form/res.partner', data={'name': 'Forged'}).json())
        self.assertIn('error', self.submit({'name': 'Forged'}, model_name='mail.mail'))
        for values, files in [
            ({'website_form_signature': 'forged'}, None),
            ({'phone': '+32 123'}, None),  # not an input of the form
            ({'Department': 'Admin'}, None),  # not an option of the input
            ({'Department': 'Sales,Support'}, None),  # several options of a single choice
            ({'Topics': 'Delivery,Admin'}, None), # Admin is not an allowed checkbox option
            ({'name': ''}, None),  # required
            ({'country_id': ''}, None),  # the state of any country is required
            ({'country_id': '1'}, None),  # the state of the country is required
            ({'Message': 'Hello you'}, None),  # requirement
            ({'Message': 'Odoo'}, None),  # min length
            ({'Message': 'Odoo rocks!'}, None),  # max length
            ({'email': 'forged'}, None),
            ({'Age': '17'}, None),
            ({'Age': 'eighteen'}, None),
            ({'Age': '18.5'}, None),  # step
            ({'Date': (date.today() - timedelta(days=2)).strftime('%m/%d/%Y')}, None),
            ({}, {'Photo [image][0][0]': ('forged.txt', b'forged', 'text/plain')}),
            ({}, {'Photo [image][0][0]': ('forged.png', b'0' * 1_000_001, 'image/png')}),
            ({}, {'Photo [image][0][0]': ('photo.png', b'photo', 'image/png'), 'Photo [image][0][1]': ('forged.png', b'forged', 'image/png')}),
            ({'Photo [image]': 'forged'}, None),
        ]:
            with self.subTest(values=values, files=files):
                self.assertIn('error', self.submit({'name': 'Forged', 'country_id': '2', **values}, files=files))
        self.assertFalse(self.env['res.partner'].search([('name', '=', 'Forged')]))
