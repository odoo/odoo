# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools import Query, SQL


class QueryTestCase(BaseCase):

    def test_basic_query(self):
        query = Query(None, 'product_product')
        query.add_table('product_template')
        query.add_where("product_product.template_id = product_template.id")
        # add inner join
        alias = query.join("product_template", "categ_id", "product_category", "id", "categ_id")
        self.assertEqual(alias, 'product_template__categ_id')
        # add left join
        alias = query.left_join("product_product", "user_id", "res_user", "id", "user_id")
        self.assertEqual(alias, 'product_product__user_id')

        self.assertEqual(query.from_clause.code,
            '"product_product", "product_template" JOIN "product_category" AS "product_template__categ_id" ON ("product_template"."categ_id" = "product_template__categ_id"."id") LEFT JOIN "res_user" AS "product_product__user_id" ON ("product_product"."user_id" = "product_product__user_id"."id")')
        self.assertEqual(query.where_clause.code,
            "product_product.template_id = product_template.id")

    def test_query_chained_explicit_joins(self):
        query = Query(None, 'product_product')
        query.add_table('product_template')
        query.add_where("product_product.template_id = product_template.id")
        # add inner join
        alias = query.join("product_template", "categ_id", "product_category", "id", "categ_id")
        self.assertEqual(alias, 'product_template__categ_id')
        # add CHAINED left join
        alias = query.left_join("product_template__categ_id", "user_id", "res_user", "id", "user_id")
        self.assertEqual(alias, 'product_template__categ_id__user_id')

        self.assertEqual(query.from_clause.code,
            '"product_product", "product_template" JOIN "product_category" AS "product_template__categ_id" ON ("product_template"."categ_id" = "product_template__categ_id"."id") LEFT JOIN "res_user" AS "product_template__categ_id__user_id" ON ("product_template__categ_id"."user_id" = "product_template__categ_id__user_id"."id")')
        self.assertEqual(query.where_clause.code,
            "product_product.template_id = product_template.id")

    def test_mixed_query_chained_explicit_implicit_joins(self):
        query = Query(None, 'product_product')
        query.add_table('product_template')
        query.add_where("product_product.template_id = product_template.id")
        # add inner join
        alias = query.join("product_template", "categ_id", "product_category", "id", "categ_id")
        self.assertEqual(alias, 'product_template__categ_id')
        # add CHAINED left join
        alias = query.left_join("product_template__categ_id", "user_id", "res_user", "id", "user_id")
        self.assertEqual(alias, 'product_template__categ_id__user_id')
        # additional implicit join
        query.add_table('account_account')
        query.add_where("product_category.expense_account_id = account_account.id")

        self.assertEqual(query.from_clause.code,
            '"product_product", "product_template", "account_account" JOIN "product_category" AS "product_template__categ_id" ON ("product_template"."categ_id" = "product_template__categ_id"."id") LEFT JOIN "res_user" AS "product_template__categ_id__user_id" ON ("product_template__categ_id"."user_id" = "product_template__categ_id__user_id"."id")')
        self.assertEqual(query.where_clause.code,
            "product_product.template_id = product_template.id AND product_category.expense_account_id = account_account.id")

    def test_raise_missing_lhs(self):
        query = Query(None, 'product_product')
        with self.assertRaises(AssertionError):
            query.join("product_template", "categ_id", "product_category", "id", "categ_id")

    def test_long_aliases(self):
        query = Query(None, 'product_product')
        tmp = query.join('product_product', 'product_tmpl_id', 'product_template', 'id', 'product_tmpl_id')
        self.assertEqual(tmp, 'product_product__product_tmpl_id')
        # no hashing
        tmp_cat = query.join(tmp, 'product_category_id', 'product_category', 'id', 'product_category_id')
        self.assertEqual(tmp_cat, 'product_product__product_tmpl_id__product_category_id')
        # hashing to limit identifier length
        tmp_cat_cmp = query.join(tmp_cat, 'company_id', 'res_company', 'id', 'company_id')
        self.assertEqual(tmp_cat_cmp, 'product_product__product_tmpl_id__product_category_id__9f0ddff7')
        tmp_cat_stm = query.join(tmp_cat, 'salesteam_id', 'res_company', 'id', 'salesteam_id')
        self.assertEqual(tmp_cat_stm, 'product_product__product_tmpl_id__product_category_id__953a466f')
        # extend hashed identifiers
        tmp_cat_cmp_par = query.join(tmp_cat_cmp, 'partner_id', 'res_partner', 'id', 'partner_id')
        self.assertEqual(tmp_cat_cmp_par, 'product_product__product_tmpl_id__product_category_id__56d55687')
        tmp_cat_stm_par = query.join(tmp_cat_stm, 'partner_id', 'res_partner', 'id', 'partner_id')
        self.assertEqual(tmp_cat_stm_par, 'product_product__product_tmpl_id__product_category_id__00363fdd')

    def test_table_expression(self):
        query = Query(None, 'foo')
        from_clause = query.from_clause.code
        self.assertEqual(from_clause, '"foo"')

        query = Query(None, 'bar', SQL('(SELECT id FROM foo)'))
        from_clause = query.from_clause.code
        self.assertEqual(from_clause, '(SELECT id FROM foo) AS "bar"')

        query = Query(None, 'foo')
        query.add_table('bar', SQL('(SELECT id FROM foo)'))
        from_clause = query.from_clause.code
        self.assertEqual(from_clause, '"foo", (SELECT id FROM foo) AS "bar"')

        query = Query(None, 'foo')
        query.join('foo', 'bar_id', SQL('(SELECT id FROM foo)'), 'id', 'bar')
        from_clause = query.from_clause.code
        self.assertEqual(from_clause, '"foo" JOIN (SELECT id FROM foo) AS "foo__bar" ON ("foo"."bar_id" = "foo__bar"."id")')


class TestQuery(TransactionCase):
    def test_auto(self):
        model = self.env['res.partner.category']
        model.create([{'name': 'Test Category 1'}, {'name': 'Test Category 2'}])
        query = model._search([])
        self.assertIsInstance(query, Query)

        ids = list(query)
        self.assertGreater(len(ids), 1)

    def test_records_as_query(self):
        records = self.env['res.partner.category']
        query = records._as_query()
        self.assertEqual(list(query), records.ids)
        self.cr.execute(query.select())
        self.assertEqual([row[0] for row in self.cr.fetchall()], records.ids)

        records = self.env['res.partner.category'].search([])
        query = records._as_query()
        self.assertEqual(list(query), records.ids)
        self.cr.execute(query.select())
        self.assertEqual([row[0] for row in self.cr.fetchall()], records.ids)

        records = records.browse(reversed(records.ids))
        query = records._as_query()
        self.assertEqual(list(query), records.ids)
        self.cr.execute(query.select())
        self.assertEqual([row[0] for row in self.cr.fetchall()], records.ids)
