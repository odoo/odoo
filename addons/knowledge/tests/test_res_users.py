# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.knowledge.tests.common import KnowledgeCommon
from odoo.tests.common import tagged


@tagged('knowledge_user')
class TestResUsers(KnowledgeCommon):

    def test_onboarding_article(self):
        internal_user = self.env['res.users'].with_context(**self._test_context).create({
            'email': 'hector@example.com',
            'login': 'hector',
            'password': 'hectorhector',
            'name': 'Hector Tue',
            'groups_id': [(4, self.env.ref('base.group_user').id)],
        })
        onboarding_article = self.env['knowledge.article'].search(
            [('article_member_ids.partner_id', '=', internal_user.partner_id.id)]
        )
        self.assertMembers(onboarding_article, 'none', {internal_user.partner_id: 'write'})
        hector_article = onboarding_article.with_user(internal_user)
        self.assertTrue(hector_article.is_user_favorite)
        self.assertTrue(hector_article.name, f'Welcome {internal_user.name}')

    def test_onboarding_article_skip(self):
        portal_user = self.env['res.users'].with_context(**self._test_context).create({
            'email': 'patrick@example.com',
            'login': 'patrick',
            'password': 'patrickpatrick',
            'name': 'Patrick Hochet',
            'groups_id': [(4, self.env.ref('base.group_portal').id)],
        })
        onboarding_article = self.env['knowledge.article'].search(
            [('article_member_ids.partner_id', '=', portal_user.partner_id.id)]
        )
        self.assertFalse(onboarding_article)

        internal_user = self.env['res.users'].with_context(
            knowledge_skip_onboarding_article=True,
            **self._test_context
        ).create({
            'email': 'roberta@example.com',
            'login': 'roberta',
            'password': 'robertaroberta',
            'name': 'Roberta Rabiscotée',
            'groups_id': [(4, self.env.ref('base.group_user').id)],
        })
        onboarding_article = self.env['knowledge.article'].search(
            [('article_member_ids.partner_id', '=', internal_user.partner_id.id)]
        )
        self.assertFalse(onboarding_article)
