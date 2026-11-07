# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user, tagged, TransactionCase

from odoo.addons.mail.tools.discuss import Store


@tagged('post_install', '-at_install')
class TestChatbotRedirectRecord(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.page = cls.env['website.page'].create({
            'name': 'Chatbot Target',
            'url': '/chatbot-target',
            'type': 'qweb',
            'arch': '<div/>',
            'is_published': True,
        })
        script = cls.env['chatbot.script'].create({'title': 'Redirect Bot'})
        step = cls.env['chatbot.script.step'].create({
            'chatbot_script_id': script.id,
            'message': '<p>Where to?</p>',
            'step_type': 'question_selection',
        })
        cls.answer = cls.env['chatbot.script.answer'].create({
            'name': 'Take me there',
            'script_step_id': step.id,
            'redirect_record_ref': f'website.page,{cls.page.id}',
        })

    def test_selection_only_searchable_models(self):
        models = dict(self.env['chatbot.script.answer']._selection_redirect_record_ref())
        self.assertIn('website.page', models)
        self.assertNotIn('website.searchable.mixin', models)
        self.assertNotIn('website.located.mixin', models)
        self.assertNotIn('website.controller.page', models)
        self.assertNotIn('website.snippet.filter', models)
        self.assertNotIn('res.partner', models)
        self.assertNotIn('res.users', models)

    def test_redirect_link_follows_record(self):
        base_url = self.page.get_base_url()
        self.answer.redirect_link = '/fallback'
        data = Store().add(self.answer, '_store_script_answer_fields')._build_result()
        self.assertEqual(data['chatbot.script.answer'][0]['redirect_link'], f'{base_url}/chatbot-target')
        self.page.url = '/chatbot-target-renamed'
        data = Store().add(self.answer, '_store_script_answer_fields')._build_result()
        self.assertEqual(data['chatbot.script.answer'][0]['redirect_link'], f'{base_url}/chatbot-target-renamed')
        self.answer.redirect_record_ref = False
        data = Store().add(self.answer, '_store_script_answer_fields')._build_result()
        self.assertEqual(data['chatbot.script.answer'][0]['redirect_link'], '/fallback')

    def test_redirect_link_record_website_domain(self):
        # the livechat may run on a non-Odoo site or on another website: the link must be absolute
        website = self.env['website'].create({'name': 'My Website', 'domain': 'https://example.com'})
        self.page.website_id = website
        self.assertEqual(self.answer._get_redirect_link(), 'https://example.com/chatbot-target')

    def test_redirect_link_shared_record_current_website(self):
        website_a = self.env['website'].create({'name': 'Website A', 'domain': 'https://a.example.com'})
        website_b = self.env['website'].create({'name': 'Website B', 'domain': 'https://b.example.com'})
        self.assertFalse(self.page.website_id)
        answer_on_b = self.answer.with_context(host_id=website_b.id)
        self.assertEqual(answer_on_b._get_redirect_link(), 'https://b.example.com/chatbot-target')
        self.page.website_id = website_a
        self.assertEqual(answer_on_b._get_redirect_link(), 'https://a.example.com/chatbot-target')

    def test_unlink_linked_record(self):
        with self.assertRaisesRegex(UserError, 'Redirect Bot'):
            self.page.unlink()
        self.page.with_context(website_url_dependencies_confirmed=True).unlink()
        self.assertFalse(self.page.exists())
        self.assertFalse(self.answer.redirect_record_ref)

    def test_unlink_linked_record_forced(self):
        # theme switch: the page is deleted by cascade from its view, with `force_delete`
        self.page.view_id.with_context(force_delete=True).unlink()
        self.assertFalse(self.page.exists())
        self.assertFalse(self.answer.redirect_record_ref)

    def test_redirect_link_deleted_outside_orm(self):
        # e.g. an upgrade script deleting the view in SQL, the page goes with it by FK cascade
        self.answer.redirect_link = '/fallback'
        self.env.flush_all()
        self.env.cr.execute("DELETE FROM ir_ui_view WHERE id = %s", [self.page.view_id.id])
        self.env.invalidate_all()
        self.assertEqual(self.answer._get_redirect_link(), '/fallback')

    def test_redirect_link_model_without_website_url(self):
        # e.g. website_sale uninstalled: product.template stays, without its website fields
        self.answer.redirect_link = '/fallback'
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE chatbot_script_answer SET redirect_record_ref = %s WHERE id = %s",
            [f'res.country,{self.env.ref("base.be").id}', self.answer.id],
        )
        self.env.invalidate_all()
        self.assertEqual(self.answer._get_redirect_link(), '/fallback')

    def test_url_dependencies_without_chatbot_access(self):
        designer = new_test_user(self.env, 'designer', groups='base.group_user,website.group_website_designer')
        dependencies = self.env['website'].with_user(designer).search_url_dependencies('website.page', self.page.ids)
        self.assertNotIn(
            f'/odoo/chatbot.script/{self.answer.chatbot_script_id.id}',
            [dependency['link'] for group in dependencies.values() for dependency in group],
        )
        # the dialog could not show the answers, so its confirmation does not count
        with self.assertRaisesRegex(UserError, 'Redirect Bot'):
            self.page.with_user(designer).with_context(website_url_dependencies_confirmed=True).unlink()
        self.assertTrue(self.answer.redirect_record_ref)

    def test_archive_linked_record(self):
        with self.assertRaisesRegex(UserError, 'Redirect Bot'):
            self.page.action_archive()
        self.answer.redirect_record_ref = False
        self.page.action_archive()
        self.assertFalse(self.page.active)

    def test_link_unpublished_record(self):
        unpublished_page = self.env['website.page'].create({
            'name': 'Unpublished Target',
            'url': '/chatbot-unpublished-target',
            'type': 'qweb',
            'arch': '<div/>',
            'is_published': False,
        })
        with self.assertRaisesRegex(ValidationError, 'Unpublished Target'):
            self.answer.redirect_record_ref = unpublished_page

    def test_unpublish_linked_record(self):
        with self.assertRaisesRegex(UserError, 'Redirect Bot'):
            self.page.is_published = False
        with self.assertRaisesRegex(UserError, 'Redirect Bot'):
            self.page.website_published = False
        with self.assertRaisesRegex(UserError, 'Redirect Bot'):
            self.page.publish_on = '2100-01-01 00:00:00'
        self.answer.redirect_record_ref = False
        self.page.is_published = False
        self.assertFalse(self.page.is_published)

    def test_url_dependencies(self):
        script_link = f'/odoo/chatbot.script/{self.answer.chatbot_script_id.id}'
        dependencies = self.env['website'].search_url_dependencies('website.page', self.page.ids)
        self.assertEqual([
            dependency['url']
            for group in dependencies.values() for dependency in group
            if dependency['link'] == script_link
        ], ['/chatbot-target'])
        self.answer.redirect_record_ref = False
        dependencies = self.env['website'].search_url_dependencies('website.page', self.page.ids)
        self.assertNotIn(
            script_link,
            [dependency['link'] for group in dependencies.values() for dependency in group],
        )

# def test_unlink_linked_model(self):
    #     class ChatbotRedirectTarget(models.Model):
    #         _name = 'test.chatbot.redirect.target'
    #         _description = 'Chatbot Redirect Target'
    #         _module = None
    #         _inherit = ['website.located.mixin', 'website.searchable.mixin']

    #         name = fields.Char()

    #         def _compute_website_url(self):
    #             for record in self:
    #                 record.website_url = f'/chatbot-target/{record.id}'

    #     self.env.transaction.will_change_registry()
    #     add_to_registry(self.registry, ChatbotRedirectTarget)
    #     self.addCleanup(self.registry.__delitem__, ChatbotRedirectTarget._name)
    #     self.registry._setup_models__(self.cr, [])
    #     self.registry.init_models(self.cr, [ChatbotRedirectTarget._name], {})
    #     target = self.env[ChatbotRedirectTarget._name].create({'name': 'Target'})
    #     answer = self.answer.copy({'redirect_record_ref': False})
    #     answer.redirect_record_ref = target

    #     # Model deletion drops the table without unlinking its records.
    #     model = self.env['ir.model']._get(ChatbotRedirectTarget._name)
    #     model.with_context(force_delete=True).unlink()
    #     self.assertFalse(model.exists())
    #     self.assertFalse(answer.redirect_record_ref)
    #     self.assertEqual(self.answer.redirect_record_ref, self.page)
