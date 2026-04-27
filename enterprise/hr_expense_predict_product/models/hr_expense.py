# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
import re

import psycopg2.errors

from odoo import api, fields, models, _


class HrExpense(models.Model):
    _inherit = ['hr.expense']

    # Description is the field from which we would find the product
    # Limit_parameter should be the limit of expenses to analyse ( 10000 seems to be the best )
    predicted_category = fields.Selection(
        selection=[
            ('toll', "Toll"),
            ('parking', "Parking"),
            ('gasoline', "Gasoline"),
            ('transport', "Transport"),
            ('miscellaneous', "Miscellaneous"),
            ('food', "Food"),
            ('accommodation', "Accommodation"),
        ],
        string="Predicted Category",
        index=True,
        default='miscellaneous')

    def _get_predict_postgres_dictionary(self):
        lang = self._context.get('lang') and self._context.get('lang')[:2]
        return {'fr': 'french'}.get(lang, 'english')

    def _predict_field(self, sql_query, description, category):
        psql_lang = self._get_predict_postgres_dictionary()
        parsed_description = re.sub("[*&()|!':<]+", " ", description)
        parsed_description = ' | '.join(parsed_description.split())
        limit_parameter = self.env["ir.config_parameter"].sudo().get_param("expense.predict.history.limit", '10000')
        params = {
            'lang': psql_lang,
            'description': parsed_description,
            'category': category,
            'company_id': self.company_id.id or self.env.company.id,
            'limit_parameter': int(limit_parameter),
        }
        # In case there is an error while parsing the to_tsquery (wrong character for example)
        # We don't want to have a traceback, instead return False
        with contextlib.suppress(psycopg2.errors.SyntaxError):
            with self.env.cr.savepoint():
                self.env.cr.execute(sql_query, params)
                result = self.env.cr.fetchone()
            if result:
                return result[1]

        return False


    def _predict_product(self, description, category = False):
        if not description:
            return False
        if not category:
            sql_query = """
                SELECT
                    max(f.rel) AS ranking,
                    f.product_id,
                    count(coalesce(f.product_id, 1)) AS count
                FROM (
                    SELECT
                        p_search.product_id,
                        ts_rank(p_search.document, query_plain) AS rel
                    FROM (
                        SELECT
                            expense.product_id,
                            (setweight(to_tsvector(%(lang)s, expense.name), 'B'))
                            AS document
                        FROM hr_expense expense
                        WHERE expense.state = 'done'
                            AND expense.company_id = %(company_id)s
                        ORDER BY expense.date DESC
                        LIMIT %(limit_parameter)s
                    ) p_search,
                    to_tsquery(%(lang)s, %(description)s) query_plain
                    WHERE (p_search.document @@ query_plain)
                ) AS f
                JOIN product_product p ON p.id = f.product_id AND p.active
                GROUP BY f.product_id
                ORDER BY ranking desc, count desc
            """
        else:
            sql_query = """
                SELECT
                    max(f.rel) AS ranking,
                    f.product_id,
                    count(coalesce(f.product_id, 1)) AS count
                FROM (
                    SELECT
                        p_search.product_id,
                        ts_rank(p_search.document, query_plain) AS rel
                    FROM (
                        SELECT
                            expense.product_id,
                            (setweight(to_tsvector(%(lang)s, expense.predicted_category), 'A'))
                            AS document
                        FROM hr_expense expense
                        WHERE expense.state = 'done'
                            AND expense.company_id = %(company_id)s
                        ORDER BY expense.date DESC
                        LIMIT %(limit_parameter)s
                    ) p_search,
                    to_tsquery(%(lang)s,  %(description)s) query_plain
                    WHERE (p_search.document @@ query_plain)
                ) AS f
                JOIN product_product p ON p.id = f.product_id AND p.active
                GROUP BY f.product_id
                ORDER BY ranking desc, count desc
            """
        return self._predict_field(sql_query, description, category)

    @api.onchange('name')
    def _onchange_predict_product(self):
        if self.name and not self.product_id:
            predicted_product_id = self._predict_product(self.name)
            default_product = self.env['product.product'].search([('can_be_expensed', '=', True)])
            if default_product:
                default_product = default_product.filtered(lambda p: p.default_code == "EXP_GEN")[:1] or default_product[0]
                self.product_id = predicted_product_id if predicted_product_id else default_product
