# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.models import Query
from odoo.tests.common import BaseCase, TransactionCase, tagged
from odoo.tools import SQL


@tagged('at_install', '-post_install')  # LEGACY at_install
class QueryTestCase(BaseCase):

    def test_basic_query(self):
        query = Query(None, 'product_product', SQL.identifier('product_product'))
        query.add_where('1=1')
        # add inner join
        template = query.join('product_product', 'product_template_id', 'product_template', 'id', 'template')
        self.assertEqual(template, 'product_product__template')
        # add left join
        alias = query.left_join("product_product", "user_id", "res_user", "id", "user_id")
        self.assertEqual(alias, 'product_product__user_id')

        self.assertEqual(query.from_clause._sql_tuple[0],
            '"product_product" JOIN "product_template" AS "product_product__template" ON ("product_product"."product_template_id" = "product_product__template"."id") LEFT JOIN "res_user" AS "product_product__user_id" ON ("product_product"."user_id" = "product_product__user_id"."id")')
        self.assertEqual(query.where_clause._sql_tuple[0],
            "1=1")

    def test_query_chained_explicit_joins(self):
        query = Query(None, 'product_product', SQL.identifier('product_product'))
        # add inner join
        template = query.join('product_product', 'product_template_id', 'product_template', 'id', 'template')
        self.assertEqual(template, 'product_product__template')
        # add CHAINED left join
        alias = query.left_join("product_product__template", "user_id", "res_user", "id", "user_id")
        self.assertEqual(alias, 'product_product__template__user_id')

        self.assertEqual(query.from_clause._sql_tuple[0],
            '"product_product" JOIN "product_template" AS "product_product__template" ON ("product_product"."product_template_id" = "product_product__template"."id") LEFT JOIN "res_user" AS "product_product__template__user_id" ON ("product_product__template"."user_id" = "product_product__template__user_id"."id")')
        self.assertFalse(query.where_clause._sql_tuple[0])

    def test_raise_missing_lhs(self):
        query = Query(None, 'product_product', SQL.identifier('product_product'))
        with self.assertRaises(AssertionError):
            query.join("product_template", "categ_id", "product_category", "id", "categ_id")

    def test_long_aliases(self):
        query = Query(None, 'product_product', SQL.identifier('product_product'))
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
        query = Query(None, 'foo', SQL.identifier('foo'))
        from_clause = query.from_clause._sql_tuple[0]
        self.assertEqual(from_clause, '"foo"')

        query = Query(None, 'bar', SQL('(SELECT id FROM foo)'))
        from_clause = query.from_clause._sql_tuple[0]
        self.assertEqual(from_clause, '(SELECT id FROM foo) AS "bar"')

        query = Query(None, 'foo', SQL.identifier('foo'))
        query.join('foo', 'bar_id', SQL('(SELECT id FROM foo)'), 'id', 'bar')
        from_clause = query.from_clause._sql_tuple[0]
        self.assertEqual(from_clause, '"foo" JOIN (SELECT id FROM foo) AS "foo__bar" ON ("foo"."bar_id" = "foo__bar"."id")')

    def test_empty_set_result_ids(self):
        query = Query(None, 'foo', SQL.identifier('foo'))
        query.set_result_ids([])
        self.assertEqual(query.get_result_ids(), ())
        self.assertTrue(query.is_empty())
        self.assertIn('SELECT', query.subselect()._sql_tuple[0], "subselect must contain SELECT")

        query.add_where(SQL("x > 0"))
        self.assertTrue(query.is_empty(), "adding where clauses keeps the result empty")

    def test_set_result_ids(self):
        query = Query(None, 'foo', SQL.identifier('foo'))
        query.set_result_ids([1, 2, 3])
        self.assertEqual(query.get_result_ids(), (1, 2, 3))
        self.assertFalse(query.is_empty())

        query.add_where(SQL("x > 0"))
        self.assertIsNone(query._ids, "adding where clause resets the ids")


@tagged('at_install', '-post_install')  # LEGACY at_install
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

    def test_raw_aliases(self):
        query = Query(None, 'foo', SQL('SELECT id FROM table'))
        table = query.table
        self.assertEqual(table._alias, 'foo')
        self.assertIsInstance(table, SQL)
        self.assertEqual(table._sql_tuple[0], '"foo"')

        column = table.stuff
        self.assertIsInstance(column, SQL)
        self.assertEqual(column._sql_tuple[0], '"foo"."stuff"')

        # make sure that on instance identifier is a property (not the static function)
        column = table.identifier
        self.assertIsInstance(column, SQL, "identifier should only be at class-level")

        # _with_model should work with any model
        category = self.env['res.partner.category']
        self.assertIs(table._with_model(category)._model, category)

    def test_model_aliases(self):
        model = self.env['res.partner.category']
        query = Query(model)
        category = query.table
        self.assertIsInstance(category, SQL)
        self.assertEqual(category._alias, model._table)
        self.assertIs(category._model, model)
        self.assertIs(category._query, query)
        self.assertEqual(category._sql_tuple[0], '"res_partner_category"')

        code, params, to_flush = category.active._sql_tuple
        self.assertEqual(code, '"res_partner_category"."active"')
        self.assertFalse(params)
        self.assertIn(model._fields['active'], to_flush)

        # name is translated, check that 'category' delegates to the field
        self.assertTrue(model._fields['name'].translate)
        code, params, to_flush = category.name._sql_tuple
        self.assertEqual(code, '"res_partner_category"."name"->>%s')
        code, params, to_flush = category._with_model(category._model.with_context(prefetch_langs=True)).name._sql_tuple
        self.assertEqual(code, '"res_partner_category"."name"')

        model = self.env['res.partner']
        query = Query(model)
        partner = query.table

        field = partner.company_id
        code, params, to_flush = field._sql_tuple
        self.assertEqual(code, '"res_partner"."company_id"')
        self.assertEqual(len(query._joins), 1, "not yet joined on company")

        company = field.id._table  # implicit join
        self.assertIsInstance(company, SQL)
        self.assertEqual(company._alias, 'res_partner__company_id')
        self.assertEqual(company._model._name, 'res.company')
        self.assertIs(company._query, query)
        self.assertEqual(len(query._joins), 2, "joined on company")

        company_field = field.name
        self.assertEqual(company_field._table._alias, company._alias)
        code, params, to_flush = company_field._sql_tuple
        self.assertEqual(code, '"res_partner__company_id"."name"')

        with self.assertQueries(['''
            SELECT "res_partner__company_id"."name"
            FROM "res_partner"
            LEFT JOIN "res_company" AS "res_partner__company_id"
                ON ("res_partner"."company_id" = "res_partner__company_id"."id")
        ''']):
            self.env.execute_query(query.select(company_field))

        # not for x2many fields, because they change the result's cardinality
        with self.assertRaisesRegex(ValueError, "Cannot generate SQL for multi-relational field res.partner.child_ids"):
            partner.child_ids
        with self.assertRaisesRegex(ValueError, "Cannot generate SQL for multi-relational field res.partner.category_id"):
            partner.category_id
