# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import psycopg2
class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    invoice_count = fields.Integer(
        "Invoice Count",
        compute='_compute_invoice_count',
    )
    vendor_bill_count = fields.Integer(
        "Vendor Bill Count",
        compute='_compute_vendor_bill_count',
    )

    @api.depends('line_ids')
    def _compute_invoice_count(self):
        sale_types = self.env['account.move'].get_sale_types(include_receipts=True)

        query = self.env['account.move.line']._search([
            ('parent_state', '=', 'posted'),
            ('move_id.move_type', 'in', sale_types),
        ])
        query.add_where(
            'account_move_line.analytic_distribution ?| %s',
            [[str(account_id) for account_id in self.ids]],
        )

        query.order = None
        query_string, query_param = query.select(
            'jsonb_object_keys(account_move_line.analytic_distribution) as account_id',
            'COUNT(DISTINCT(account_move_line.move_id)) as move_count',
        )
        query_string = f"{query_string} GROUP BY jsonb_object_keys(account_move_line.analytic_distribution)"

        self._cr.execute(query_string, query_param)
        data = {int(record.get('account_id')): record.get('move_count') for record in self._cr.dictfetchall()}
        for account in self:
            account.invoice_count = data.get(account.id, 0)

    @api.depends('line_ids')
    def _compute_vendor_bill_count(self):
        purchase_types = self.env['account.move'].get_purchase_types(include_receipts=True)

        query = self.env['account.move.line']._search([
            ('parent_state', '=', 'posted'),
            ('move_id.move_type', 'in', purchase_types),
        ])
        query.add_where(
            'account_move_line.analytic_distribution ?| %s',
            [[str(account_id) for account_id in self.ids]],
        )

        query.order = None
        query_string, query_param = query.select(
            'jsonb_object_keys(account_move_line.analytic_distribution) as account_id',
            'COUNT(DISTINCT(account_move_line.move_id)) as move_count',
        )
        query_string = f"{query_string} GROUP BY jsonb_object_keys(account_move_line.analytic_distribution)"

        self._cr.execute(query_string, query_param)
        data = {int(record.get('account_id')): record.get('move_count') for record in self._cr.dictfetchall()}
        for account in self:
            account.vendor_bill_count = data.get(account.id, 0)

    @api.ondelete(at_uninstall=False)
    def _unlink_check_for_existing_analytic_distribution(self):
        # check if the analytic line is linked to a record
        # get all tables that has a column name called 'analytic_distribution'
        self.env.cr.execute(
            """
                SELECT T.table_name
                FROM information_schema.tables T
                INNER JOIN information_schema.columns C ON C.table_name = T.table_name AND C.table_schema = T.table_schema
                WHERE C.column_name LIKE 'analytic_distribution'
                AND T.table_schema NOT IN ('information_schema', 'pg_catalog')
                AND T.table_type = 'BASE TABLE'
            """
            )
        all_tables_name = self.env.cr.fetchall()

        for table_name in all_tables_name:
            query = psycopg2.sql.SQL(
                """
                    SELECT COUNT(id)
                    FROM {table_name}
                    WHERE analytic_distribution->'%s' IS NOT NULL
                """).format(
                        table_name=psycopg2.sql.Identifier(table_name[0])
                    )
            self.env.cr.execute(query, [self.id])
            rslt = self.env.cr.fetchone()[0]
            if rslt > 0:
                model_desc = self.env[table_name[0].replace('_', '.', -1)]._description
                raise UserError(_(
                        "Deletion of this analytic line is not possible due to its utilization in certain records within the model %s, Please consider archiving it instead.",
                        model_desc))

    def action_view_invoice(self):
        self.ensure_one()
        query = self.env['account.move.line']._search([('move_id.move_type', 'in', self.env['account.move'].get_sale_types())])
        query.order = None
        query.add_where('analytic_distribution ? %s', [str(self.id)])
        query_string, query_param = query.select('DISTINCT account_move_line.move_id')
        self._cr.execute(query_string, query_param)
        move_ids = [line.get('move_id') for line in self._cr.dictfetchall()]
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False, 'default_move_type': 'out_invoice'},
            "name": _("Customer Invoices"),
            'view_mode': 'tree,form',
        }
        return result

    def action_view_vendor_bill(self):
        self.ensure_one()
        query = self.env['account.move.line']._search([('move_id.move_type', 'in', self.env['account.move'].get_purchase_types())])
        query.order = None
        query.add_where('analytic_distribution ? %s', [str(self.id)])
        query_string, query_param = query.select('DISTINCT account_move_line.move_id')
        self._cr.execute(query_string, query_param)
        move_ids = [line.get('move_id') for line in self._cr.dictfetchall()]
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move_ids)],
            "context": {"create": False, 'default_move_type': 'in_invoice'},
            "name": _("Vendor Bills"),
            'view_mode': 'tree,form',
        }
        return result
