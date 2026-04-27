# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from lxml import html
from markupsafe import Markup

from odoo.tests.common import tagged, HttpCase
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'knowledge_article_template')
class TestKnowledgeArticleTemplate(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Article = cls.env["knowledge.article"]
        Category = cls.env["knowledge.article.template.category"]
        Stage = cls.env["knowledge.article.stage"]

        with mute_logger("odoo.models.unlink"):
            Article.search([]).unlink()
            Category.search([]).unlink()
            Stage.search([]).unlink()

        cls.article = Article.create({
            "body": Markup("<p>Hello world</p>"),
            "name": "My Article",
        })

        cls.personal_category = Category.create({
            "name": "Personal"
        })

        cls.template = Article.create({
            "icon": "emoji",
            "is_template": True,
            "template_name": "Template",
            "template_body": Markup("<p>Lorem ipsum dolor sit amet</p>"),
            "template_category_id": cls.personal_category.id,
        })
        cls.child_template_1 = Article.create({
            "parent_id": cls.template.id,
            "article_properties_definition": [{
                "name": "28db68689e91de10",
                "type": "char",
                "string": "My Text Field",
                "default": ""
            }],
            "is_template": True,
            "template_name": "Child 1",
            "template_body": Markup("""
                <p>Sint dicta facere eum excepturi</p>
                <div data-embedded="view" data-oe-protected="true" data-embedded-props="{
                    'viewProps': {
                        'actionXmlId': 'knowledge.knowledge_article_item_action',
                        'displayName': 'Article Items',
                        'viewType': 'list',
                        'context': {
                            'active_id': ref('knowledge.knowledge_article_template_test'),
                            'default_parent_id': ref('knowledge.knowledge_article_template_test'),
                            'default_is_article_item': True
                        }
                    }
                }"/>
            """),
            "template_category_id": cls.personal_category.id,
        })

        cls.env["ir.model.data"].create({
            "module": "knowledge",
            "name": "knowledge_article_template_test",
            "model": "knowledge.article",
            "res_id": cls.child_template_1.id
        })

        cls.child_template_1_stage_new = Stage.create({
            "name": "New",
            "sequence": 1,
            "fold": False,
            "parent_id": cls.child_template_1.id,
        })
        cls.child_template_1_stage_ongoing = Stage.create({
            "name": "Ongoing",
            "sequence": 2,
            "fold": False,
            "parent_id": cls.child_template_1.id,
        })

        cls.child_template_1_1 = Article.create({
            "parent_id": cls.child_template_1.id,
            "article_properties": {
                "28db68689e91de10": "Hi there"
            },
            "is_template": True,
            "template_name": "Child 1.1",
            "template_body": Markup("<p>Magni labore natus, sunt consequatur error</p>"),
            "template_category_id": cls.personal_category.id,
        })
        cls.child_template_1_2 = Article.create({
            "parent_id": cls.child_template_1.id,
            "is_template": True,
            "template_name": "Child 1.2",
            "template_body": Markup("<p>Ullam molestias error commodi dignissimos</p>"),
            "template_category_id": cls.personal_category.id,
        })
        cls.child_template_1_3 = Article.create({
            "parent_id": cls.child_template_1.id,
            "is_article_item": True,
            "stage_id": cls.child_template_1_stage_new.id,
            "is_template": True,
            "template_name": "Child 1.3",
            "template_body": Markup("<p>Commodi voluptatem inventore quod iure</p>"),
            "template_category_id": cls.personal_category.id,
        })
        cls.child_template_1_4 = Article.create({
            "parent_id": cls.child_template_1.id,
            "is_article_item": True,
            "stage_id": cls.child_template_1_stage_ongoing.id,
            "is_template": True,
            "template_name": "Child 1.4",
            "template_body": Markup("<p>Facilis esse ipsam quidem consectetur</p>"),
            "template_category_id": cls.personal_category.id,
        })
        cls.child_template_2 = Article.create({
            "parent_id": cls.template.id,
            "is_template": True,
            "template_name": "Child 2",
            "template_body": Markup("<p>Voluptate autem officia</p>"),
            "template_category_id": cls.personal_category.id,
        })

    def test_apply_template(self):
        """ Check that that a given template is properly applied to a given article. """
        dummy_article = self.env['knowledge.article'].create({'name': 'NoBody', 'body': False})
        dummy_article.apply_template(self.template.id, skip_body_update=True)
        self.assertFalse(dummy_article.body)
        self.assertEqual(dummy_article.icon, self.template.icon)

        self.article.apply_template(self.template.id, skip_body_update=False)

        # After applying the template on the article, the values of the article
        # should have been updated and new child articles should have been created
        # for the article.

        # First level:
        self.assertEqual(self.article.body, Markup("<p>Lorem ipsum dolor sit amet</p>"))
        self.assertEqual(self.article.icon, self.template.icon)
        self.assertEqual(len(self.article.child_ids), 2)
        self.assertFalse(self.article.is_article_item)
        self.assertFalse(self.article.is_template)
        self.assertFalse(self.article.stage_id)

        # Second level:
        [child_article_1, child_article_2] = self.article.child_ids.sorted("name")
        self.assertEqual(child_article_1.article_properties_definition, [{
            "name": "28db68689e91de10",
            "type": "char",
            "string": "My Text Field",
            "default": ""
        }])

        # Check that the ids stored in the embedded view have properly been updated
        # to refer to the parent article.

        fragment = html.fragment_fromstring(child_article_1.body, create_parent="div")
        embedded_views = list(fragment.xpath("//*[@data-embedded='view']"))

        self.assertEqual(len(embedded_views), 1)
        embedded_props = json.loads(embedded_views[0].get("data-embedded-props"))
        self.assertEqual(embedded_props, {
            "viewProps": {
                "actionXmlId": "knowledge.knowledge_article_item_action",
                "displayName": "Article Items",
                "viewType": "list",
                "context": {
                    "active_id": child_article_1.id,
                    "default_parent_id": child_article_1.id,
                    "default_is_article_item": True
                }
            }
        })

        self.assertTrue(len(child_article_1.child_ids), 4)
        self.assertFalse(child_article_1.is_article_item)
        self.assertFalse(child_article_1.is_template)
        self.assertFalse(child_article_1.stage_id)

        self.assertEqual(child_article_2.body, Markup("<p>Voluptate autem officia</p>"))
        self.assertFalse(child_article_2.child_ids)
        self.assertFalse(child_article_2.is_article_item)
        self.assertFalse(child_article_2.is_template)
        self.assertFalse(child_article_2.stage_id)

        # Third level:
        [child_article_1_1, child_article_1_2, child_article_1_3, child_article_1_4] = child_article_1.child_ids.sorted("name")
        self.assertEqual(child_article_1_1.article_properties, {
            "28db68689e91de10": "Hi there"
        })
        self.assertEqual(child_article_1_1.body, Markup("<p>Magni labore natus, sunt consequatur error</p>"))
        self.assertFalse(child_article_1_1.child_ids)
        self.assertFalse(child_article_1_1.is_article_item)
        self.assertFalse(child_article_1_1.is_template)
        self.assertFalse(child_article_1_1.stage_id)

        self.assertEqual(child_article_1_2.body, Markup("<p>Ullam molestias error commodi dignissimos</p>"))
        self.assertFalse(child_article_1_2.child_ids)
        self.assertFalse(child_article_1_2.is_article_item)
        self.assertFalse(child_article_1_2.is_template)
        self.assertFalse(child_article_1_2.stage_id)

        [child_article_1_stage_new, child_article_1_stage_ongoing] = \
            self.env["knowledge.article.stage"].search([("parent_id", "=", child_article_1.id)]).sorted("name")

        self.assertEqual(child_article_1_3.body, Markup("<p>Commodi voluptatem inventore quod iure</p>"))
        self.assertFalse(child_article_1_3.child_ids)
        self.assertTrue(child_article_1_3.is_article_item)
        self.assertFalse(child_article_1_3.is_template)
        self.assertEqual(child_article_1_3.stage_id, child_article_1_stage_new)

        self.assertEqual(child_article_1_4.body, Markup("<p>Facilis esse ipsam quidem consectetur</p>"))
        self.assertFalse(child_article_1_4.child_ids)
        self.assertTrue(child_article_1_4.is_article_item)
        self.assertFalse(child_article_1_4.is_template)
        self.assertEqual(child_article_1_4.stage_id, child_article_1_stage_ongoing)

    def test_template_category_inheritance(self):
        """ Check that the category of the child templates remain always
            consistent with the root template. """

        new_category = self.env["knowledge.article.template.category"].create({
            "name": "New Category"
        })

        # When the user updates the category of a template having a parent,
        # the category of the template should be reset.

        self.child_template_1.write({
            "template_category_id": new_category.id
        })
        self.assertEqual(self.template.template_category_id, self.personal_category)
        self.assertEqual(self.child_template_1.template_category_id, self.personal_category)
        self.assertEqual(self.child_template_1_1.template_category_id, self.personal_category)
        self.assertEqual(self.child_template_1_2.template_category_id, self.personal_category)
        self.assertEqual(self.child_template_1_3.template_category_id, self.personal_category)
        self.assertEqual(self.child_template_1_4.template_category_id, self.personal_category)
        self.assertEqual(self.child_template_2.template_category_id, self.personal_category)

        # When the user updates the category of the root template, the category
        # of all child templates should be updated.

        self.template.write({
            "template_category_id": new_category.id
        })
        self.assertEqual(self.template.template_category_id, new_category)
        self.assertEqual(self.child_template_1.template_category_id, new_category)
        self.assertEqual(self.child_template_1_1.template_category_id, new_category)
        self.assertEqual(self.child_template_1_2.template_category_id, new_category)
        self.assertEqual(self.child_template_1_3.template_category_id, new_category)
        self.assertEqual(self.child_template_1_4.template_category_id, new_category)
        self.assertEqual(self.child_template_2.template_category_id, new_category)

    def test_template_hierarchy(self):
        """ Check that the templates are properly linked to each other. """
        self.assertFalse(self.article.child_ids)
        # Check 'child_ids' field:
        self.assertEqual(self.template.child_ids, self.child_template_1 + self.child_template_2)
        self.assertEqual(self.child_template_1.child_ids, \
            self.child_template_1_1 + self.child_template_1_2 + self.child_template_1_3 + self.child_template_1_4)
        self.assertFalse(self.child_template_2.child_ids)
        # Check 'parent_id' field:
        self.assertFalse(self.template.parent_id)
        self.assertEqual(self.child_template_1.parent_id, self.template)
        self.assertEqual(self.child_template_1_1.parent_id, self.child_template_1)
        self.assertEqual(self.child_template_1_2.parent_id, self.child_template_1)
        self.assertEqual(self.child_template_1_3.parent_id, self.child_template_1)
        self.assertEqual(self.child_template_1_4.parent_id, self.child_template_1)
        self.assertEqual(self.child_template_2.parent_id, self.template)
