# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 OpenERP S.A. http://www.openerp.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import unittest
from openerp.osv.query import Query


class QueryTestCase(unittest.TestCase):

    def test_basic_query(self):
        query = Query()
        query.tables.extend(['"product_product"', '"product_template"'])
        query.where_clause.append("product_product.template_id = product_template.id")
        query.add_join(("product_template", "product_category", "categ_id", "id", "categ_id"), implicit=False, outer=False)  # add normal join
        query.add_join(("product_product", "res_user", "user_id", "id", "user_id"), implicit=False, outer=True)  # outer join
        self.assertEquals(query.get_sql()[0].strip(),
            """"product_product" LEFT JOIN "res_user" as "product_product__user_id" ON ("product_product"."user_id" = "product_product__user_id"."id"),"product_template" JOIN "product_category" as "product_template__categ_id" ON ("product_template"."categ_id" = "product_template__categ_id"."id") """.strip())
        self.assertEquals(query.get_sql()[1].strip(), """product_product.template_id = product_template.id""".strip())

    def test_query_chained_explicit_joins(self):
        query = Query()
        query.tables.extend(['"product_product"', '"product_template"'])
        query.where_clause.append("product_product.template_id = product_template.id")
        query.add_join(("product_template", "product_category", "categ_id", "id", "categ_id"), implicit=False, outer=False)  # add normal join
        query.add_join(("product_template__categ_id", "res_user", "user_id", "id", "user_id"), implicit=False, outer=True)  # CHAINED outer join
        self.assertEquals(query.get_sql()[0].strip(),
            """"product_product","product_template" JOIN "product_category" as "product_template__categ_id" ON ("product_template"."categ_id" = "product_template__categ_id"."id") LEFT JOIN "res_user" as "product_template__categ_id__user_id" ON ("product_template__categ_id"."user_id" = "product_template__categ_id__user_id"."id")""".strip())
        self.assertEquals(query.get_sql()[1].strip(), """product_product.template_id = product_template.id""".strip())

    def test_mixed_query_chained_explicit_implicit_joins(self):
        query = Query()
        query.tables.extend(['"product_product"', '"product_template"'])
        query.where_clause.append("product_product.template_id = product_template.id")
        query.add_join(("product_template", "product_category", "categ_id", "id", "categ_id"), implicit=False, outer=False)  # add normal join
        query.add_join(("product_template__categ_id", "res_user", "user_id", "id", "user_id"), implicit=False, outer=True)  # CHAINED outer join
        query.tables.append('"account.account"')
        query.where_clause.append("product_category.expense_account_id = account_account.id")  # additional implicit join
        self.assertEquals(query.get_sql()[0].strip(),
            """"product_product","product_template" JOIN "product_category" as "product_template__categ_id" ON ("product_template"."categ_id" = "product_template__categ_id"."id") LEFT JOIN "res_user" as "product_template__categ_id__user_id" ON ("product_template__categ_id"."user_id" = "product_template__categ_id__user_id"."id"),"account.account" """.strip())
        self.assertEquals(query.get_sql()[1].strip(), """product_product.template_id = product_template.id AND product_category.expense_account_id = account_account.id""".strip())

    def test_raise_missing_lhs(self):
        query = Query()
        query.tables.append('"product_product"')
        self.assertRaises(AssertionError, query.add_join, ("product_template", "product_category", "categ_id", "id", "categ_id"), implicit=False, outer=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
