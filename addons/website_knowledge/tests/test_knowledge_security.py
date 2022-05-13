# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.knowledge.tests.common import KnowledgeArticlePermissionsCase
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('knowledge_acl')
class TestWKnowledgeSecurity(KnowledgeArticlePermissionsCase):

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('user_public')
    def test_models_as_public(self):
        """ Test publish flag giving read access to articles """
        article_shared = self.article_roots[2].with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: Internal permission 'none', not for public"):
            article_shared.body  # access body should trigger acls

        article_shared.sudo().website_published = True
        article_shared.body  # access body should not trigger acls

        # FAVOURITE
        with self.assertRaises(exceptions.AccessError, msg='ACLs: No favorite access to public'):
            article_shared.is_user_favorite

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('portal_test')
    def test_models_as_portal(self):
        """ Test publish flag giving read access to articles """
        article_shared = self.article_roots[2].with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: Internal permission 'none', not for portal"):
            article_shared.body  # access body should trigger acls

        article_shared.sudo().website_published = True
        article_shared.body  # access body should trigger acls
        self.assertFalse(article_shared.is_user_favorite)

        # Read access gives access to favorite toggling
        article_shared.action_toggle_favorite()
        article_shared.invalidate_cache(fnames=['is_user_favorite'])
        self.assertTrue(article_shared.is_user_favorite)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('portal_test')
    def test_models_as_user(self):
        """ Test publish flag giving read access to articles """
        article_hidden = self.article_read_contents[3].with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: 'none' internal permission"):
            article_hidden.body  # access body should trigger acls

        article_hidden.sudo().website_published = True
        article_hidden.body  # access body should trigger acls
        self.assertFalse(article_hidden.is_user_favorite)

        # Read access gives access to favorite toggling
        article_hidden.action_toggle_favorite()
        article_hidden.invalidate_cache(fnames=['is_user_favorite'])
        self.assertTrue(article_hidden.is_user_favorite)
