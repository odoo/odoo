# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import tagged, TransactionCase


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
        })
        script = cls.env['chatbot.script'].create({'title': 'Redirect Bot'})
        step = cls.env['chatbot.script.step'].create({
            'chatbot_script_id': script.id,
            'message': 'Where to?',
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
        self.assertEqual(self.answer._get_redirect_link(), '/chatbot-target')
        self.page.url = '/chatbot-target-renamed'
        self.assertEqual(self.answer._get_redirect_link(), '/chatbot-target-renamed')

    def test_unlink_linked_record(self):
        with self.assertRaisesRegex(UserError, 'Redirect Bot'):
            self.page.unlink()
        self.answer.redirect_record_ref = False
        self.page.unlink()
