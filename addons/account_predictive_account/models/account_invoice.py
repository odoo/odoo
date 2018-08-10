# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import re


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    def _get_predict_postgres_dictionary(self):
        # According to our test, it is not necessary to return the postgres lang dictionary
        # But this method can be overwritten in case user would want to use a specific lang
        # for the search
        return 'simple'

    @api.multi
    def _predict_account(self, description, partner):
        # This method uses postgres tsvector in order to try to deduce the account_id of an invoice line
        # based on the text entered into the name (description) field.
        # We give some more weight to search with the same partner_id (roughly 20%) in order to have better result
        # We only limit the search on the previous 10000 entries, which according to our tests bore the best
        # results. However this limit parameter is configurable by creating a config parameter with the key:
        # account.bill.predict.history.limit

        # For information, the tests were executed with a dataset of 40 000 bills from a live database, We splitted
        # the dataset in 2, removing the 5000 most recent entries and we tried to use this method to guess the account
        # of this validation set based on the previous entries.
        # The result is roughly 90% of success.
        if not description or not partner:
            return False

        psql_lang = self._get_predict_postgres_dictionary()

        sqlQuery = """
            SELECT
                max(f.rel) AS ranking,
                f.account_id,
                count(f.account_id) AS count
            FROM (
                SELECT
                    p_search.account_id,
                    ts_rank(p_search.document, query_plain) AS rel
                FROM (
                    SELECT
                        ail.account_id,
                        (setweight(to_tsvector(%(lang)s, ail.name), 'B')) ||
                        (setweight(to_tsvector('simple', p.display_name), 'A')) AS document
                    FROM account_invoice_line ail
                    JOIN account_invoice inv
                        ON ail.invoice_id = inv.id
                    JOIN res_partner p
                        ON p.id = ail.partner_id
                    WHERE inv.type = 'in_invoice'
                        AND inv.state NOT IN ('draft', 'cancel')
                        AND ail.company_id = %(company_id)s
                    ORDER BY inv.date_invoice DESC
                    LIMIT %(limit_parameter)s
                ) p_search,
                to_tsquery(%(lang)s, %(description)s) query_plain
                WHERE (p_search.document @@ query_plain)
            ) AS f
            GROUP BY f.account_id
            ORDER BY ranking desc, count desc
        """
        description += ' ' + partner.display_name
        parsed_description = re.sub("[*&()|!':]+", " ", description)
        parsed_description = ' | '.join(parsed_description.split())
        limit_parameter = self.env["ir.config_parameter"].sudo().get_param("account.bill.predict.history.limit", '10000')
        params = {
            'lang': psql_lang,
            'description': parsed_description,
            'company_id': self.company_id.id or self.env.user.company_id.id,
            'limit_parameter': int(limit_parameter)
        }
        try:
            self.env.cr.execute(sqlQuery, params)
            result = self.env.cr.fetchone()
            if result:
                return result[1]
        except Exception as e:
            # In case there is an error while parsing the to_tsquery (wrong character for example)
            # We don't want to have a traceback, instead return False
            return False
        return False

    @api.onchange('name')
    def _onchange_name(self):
        if self.invoice_id.type == 'in_invoice' and self.name:
            account_id = self._predict_account(self.name, self.partner_id)
            # Only change account if we find a better matching one
            if account_id:
                self.account_id = account_id
