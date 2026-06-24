from odoo import api, fields, models
from odoo.models import LazySQL, TableSQL
from odoo.tools import SQL

from odoo.addons.account.models.account_move import PAYMENT_STATE_SELECTION


def related_sql(path, fname=None):
    def _related_sql(self, table):
        lazy_table = next(iter(table._query._joins.values()))[1]  # the `_table_query` of this model is a `LazySQL`
        current = lazy_table
        for part in path.split('.'):
            current = current[part]
        return SQL("%s.%s", SQL.identifier(self._table), lazy_table._select(fname, current))
    fname = fname or path.split('.')[-1]
    return {
        'compute': '_compute_from_sql',
        'compute_sql': _related_sql,
        'compute_sudo': True,
    }


def compute_sql(fname, func):
    def add_alias(self, table):
        lazy_table = next(iter(table._query._joins.values()))[1]  # the `_table_query` of this model is a `LazySQL`
        return SQL("%s.%s", SQL.identifier(self._table), lazy_table._select(fname, func(self, lazy_table)))
    return {
        'compute': '_compute_from_sql',
        'compute_sql': add_alias,
        'compute_sudo': True,
    }


class AccountInvoiceReport(models.Model):
    _name = 'account.invoice.report'
    _description = "Invoices Statistics"
    _auto = False
    _rec_name = 'invoice_date'
    _order = 'invoice_date desc'

    # ==== Invoice fields ====
    move_id = fields.Many2one('account.move', **related_sql('move_id'))
    journal_id = fields.Many2one('account.journal', string='Journal', **related_sql('journal_id'))
    company_id = fields.Many2one('res.company', string='Company', **related_sql('company_id'))
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', **related_sql('company_currency_id'))
    partner_id = fields.Many2one('res.partner', 'Partner', **related_sql('move_id.partner_id'))
    commercial_partner_id = fields.Many2one('res.partner', 'Main Partner', **related_sql('partner_id', 'commercial_partner_id'))
    country_id = fields.Many2one('res.country', "Country", **related_sql('partner_id.country_id'))
    invoice_user_id = fields.Many2one('res.users', 'Salesperson', **related_sql('move_id.user_id', 'invoice_user_id'))
    move_type = fields.Selection(
        selection=[
            ('entry', 'Journal Entry'),
            ('out_invoice', 'Customer Invoice'),
            ('out_refund', 'Customer Credit Note'),
            ('in_invoice', 'Vendor Bill'),
            ('in_refund', 'Vendor Credit Note'),
            ('out_receipt', 'Sales Receipt'),
            ('in_receipt', 'Purchase Receipt'),
        ],
        **related_sql('move_id.move_type'),
    )
    state = fields.Selection(
        string='Invoice Status',
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ],
        **related_sql('move_id.state'),
    )
    payment_state = fields.Selection(string='Payment Status', selection=PAYMENT_STATE_SELECTION, **related_sql('move_id.payment_state'))
    fiscal_position_id = fields.Many2one('account.fiscal.position', 'Fiscal Position', **related_sql('move_id.fiscal_position_id'))
    invoice_date = fields.Date(**related_sql('move_id.invoice_date'))

    # ==== Invoice line fields ====
    quantity = fields.Float('Product Quantity', **compute_sql('quantity', lambda self, table: SQL("%s * %s", self._sql_quantity(table), self._sql_in_out_sign(table))))
    product_id = fields.Many2one('product.product', 'Product', **related_sql('product_id'))
    product_uom_id = fields.Many2one('uom.uom', 'Unit', **related_sql('product_id.uom_id', 'product_uom_id'))
    product_categ_id = fields.Many2one('product.category', 'Product Category', **related_sql('product_id.categ_id', 'product_categ_id'))
    invoice_date_due = fields.Date('Due Date', **related_sql('move_id.invoice_date_due'))
    account_id = fields.Many2one('account.account', string='Revenue/Expense Account', **related_sql('account_id'))
    price_subtotal_currency = fields.Float(string='Untaxed Amount in Currency', **compute_sql('price_subtotal_currency', lambda self, table: SQL("%s * %s", table.price_subtotal, self._sql_in_out_sign(table))))
    price_subtotal = fields.Float(string='Untaxed Amount', **compute_sql('price_subtotal', lambda self, table: SQL("-%s", table.consolidation_balance)))
    price_total = fields.Float(string='Total', **compute_sql('price_total', lambda self, table: SQL("%s * %s / %s", table.price_subtotal, self._sql_in_out_sign(table), table.move_id.invoice_currency_rate)))
    price_total_currency = fields.Float(string='Total in Currency', **compute_sql('price_total_currency', lambda self, table: SQL("%s * %s", table.price_total, self._sql_in_out_sign(table))))
    price_average = fields.Float('Average Price', aggregator="avg", **compute_sql('price_average', lambda self, table: self._compute_sql_price_average(table)))
    price_margin = fields.Float(string='Margin', **compute_sql('price_margin', lambda self, table: self._compute_sql_price_margin(table)))
    inventory_value = fields.Float(string='Inventory Value', **compute_sql('inventory_value', lambda self, table: self._compute_sql_inventory_value(table)))
    currency_id = fields.Many2one('res.currency', 'Currency', **related_sql('currency_id'))

    @property
    def _table_query(self) -> SQL:
        today = fields.Date.context_today(self)
        query = self.env['account.move.line'].sudo().with_context(date_to=today)._search([
            ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')),
            ('account_id', '!=', False),
            ('display_type', '=', 'product'),
        ])
        lazy_table = LazySQL(query.table)
        lazy_table._select('id', query.table.id)
        return lazy_table

    def _sql_quantity(self, table):
        uom_ratio = SQL("(COALESCE(%s, 1) / NULLIF(COALESCE(%s, 1), 0.0))", table.product_uom_id.factor, table.product_id.uom_id.factor)
        return SQL("%s * %s", table.quantity, uom_ratio)

    def _sql_in_out_sign(self, table):
        return SQL("CASE WHEN %s IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END", table.move_id.move_type)

    def _compute_from_sql(self):
        query = self._as_query()
        table = query.table
        fields_to_fetch = [field for field in self._fields.values() if field.compute_sql]
        fetched_vals = {v['id']: v for v in self.env.execute_query_dict(query.select(
            table.id,
            *[field.compute_sql(self, table) for field in fields_to_fetch]
        ))}
        for record in self:
            for field in fields_to_fetch:
                record[field.name] = fetched_vals[record._origin.id][field.name]

    def _compute_sql_price_average(self, table: TableSQL):
        return SQL(
            "-COALESCE((%s / NULLIF(%s, 0.0)) * %s, 0.0)",
            table.consolidation_balance, self._sql_quantity(table), self._sql_in_out_sign(table),
        )

    def _compute_sql_price_margin(self, table: TableSQL):
        quantity = self._sql_quantity(table)
        table_with_company = table._with_model(table._model.with_context(sql_company_id=table.company_id))
        return SQL(
            """CASE
                WHEN %s NOT IN ('out_invoice', 'out_receipt', 'out_refund') THEN 0.0
                WHEN %s = 'out_refund' THEN %s * (-%s + %s * COALESCE(%s, 0.0))
                ELSE %s * (-%s - %s * COALESCE(%s, 0.0))
            END""",
            table.move_type,
            table.move_type, table.consolidation_rate, table.balance, quantity, table_with_company.product_id.standard_price,
            table.consolidation_rate, table.balance, quantity, table_with_company.product_id.standard_price,
        )

    def _compute_sql_inventory_value(self, table: TableSQL):
        in_out_sign = self._sql_in_out_sign(table)
        quantity = self._sql_quantity(table)
        table_with_company = table._with_model(table._model.with_context(sql_company_id=table.company_id))
        return SQL(
            "-%s * %s * %s * COALESCE(%s, 0.0)",
            table.consolidation_rate, quantity, in_out_sign, table_with_company.product_id.standard_price,
        )

    def _read_group_select(self, table: TableSQL, aggregate_spec: str) -> SQL:
        """ This override allows us to correctly calculate the average price of products. """
        if aggregate_spec != 'price_average:avg':
            return super()._read_group_select(table, aggregate_spec)
        return SQL(
            'COALESCE(SUM(%s) / NULLIF(SUM(%s), 0.0), 0)', table.price_subtotal, table.quantity,
        )


class ReportAccountReport_Invoice(models.AbstractModel):
    _name = 'report.account.report_invoice'
    _description = 'Account report without payment lines'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)

        qr_code_urls = {}
        for invoice in docs:
            if invoice.display_qr_code:
                new_code_url = invoice._generate_qr_code(silent_errors=data['report_type'] == 'html')
                if new_code_url:
                    qr_code_urls[invoice.id] = new_code_url

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'qr_code_urls': qr_code_urls,
        }


class ReportAccountReport_Invoice_With_Payments(models.AbstractModel):
    _name = 'report.account.report_invoice_with_payments'
    _description = 'Account report with payment lines'
    _inherit = ['report.account.report_invoice']

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super()._get_report_values(docids, data)
        rslt['report_type'] = data.get('report_type') if data else ''
        return rslt
