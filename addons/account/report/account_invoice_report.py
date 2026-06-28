from odoo import api, fields, models
from odoo.models import TableSQL
from odoo.tools import SQL

from odoo.addons.account.models.account_move import PAYMENT_STATE_SELECTION


class AccountInvoiceReport(models.Model):
    _name = 'account.invoice.report'
    _description = "Invoices Statistics"
    _auto = False
    _rec_name = 'invoice_date'
    _order = 'invoice_date desc'

    # ==== Invoice fields ====
    move_id = fields.Many2one('account.move', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', string='Main Partner')
    country_id = fields.Many2one('res.country', string="Country")
    invoice_user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    move_type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
        ], readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Open'),
        ('cancel', 'Cancelled')
        ], string='Invoice Status', readonly=True)
    payment_state = fields.Selection(selection=PAYMENT_STATE_SELECTION, string='Payment Status', readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True)
    invoice_date = fields.Date(readonly=True, string="Invoice Date")

    # ==== Invoice line fields ====
    quantity = fields.Float(string='Product Quantity', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    invoice_date_due = fields.Date(string='Due Date', readonly=True)
    account_id = fields.Many2one('account.account', string='Revenue/Expense Account', readonly=True)
    price_subtotal_currency = fields.Float(string='Untaxed Amount in Currency', readonly=True)
    price_subtotal = fields.Float(string='Untaxed Amount', readonly=True)
    price_total = fields.Float(string='Total', readonly=True)
    price_total_currency = fields.Float(string='Total in Currency', readonly=True)
    price_average = fields.Float(string='Average Price', readonly=True, aggregator="avg")
    price_margin = fields.Float(string='Margin', readonly=True)
    inventory_value = fields.Float(string='Inventory Value', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    @property
    def _table_query(self) -> SQL:
        today = fields.Date.context_today(self)
        query = self.env['account.move.line'].with_context(date_to=today)._search([
            ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')),
            ('account_id', '!=', False),
            ('display_type', '=', 'product'),
        ])
        return query.subselect(*self._select_list(query.table))

    def _select_list(self, table: TableSQL):
        in_out_sign = SQL("CASE WHEN %s IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END", table.move_id.move_type)
        uom_ratio = SQL("(COALESCE(%s, 1) / NULLIF(COALESCE(%s, 1), 0.0))", table.product_uom_id.factor, table.product_id.uom_id.factor)
        quantity = SQL("%s * %s", table.quantity, uom_ratio)
        table_with_company = table._with_model(table._model.with_context(sql_company_id=table.company_id))
        return [
            table.id,
            table.move_id,
            table.product_id,
            table.account_id,
            table.journal_id,
            table.company_id,
            table.currency_id,
            table.company_currency_id,
            SQL("%s AS commercial_partner_id", table.partner_id),
            SQL("%s AS user_type", table.account_id.account_type),
            table.move_id.state,
            table.move_id.move_type,
            table.move_id.partner_id,
            table.move_id.invoice_user_id,
            table.move_id.fiscal_position_id,
            table.move_id.payment_state,
            table.move_id.invoice_date,
            table.move_id.invoice_date_due,
            table.partner_id.country_id,
            SQL("%s AS product_uom_id", table.product_id.uom_id),
            SQL("%s AS product_categ_id", table.product_id.categ_id),
            SQL("%s * %s AS quantity", quantity, in_out_sign),
            SQL("%s * %s AS price_subtotal_currency", table.price_subtotal, in_out_sign),
            SQL("-%s AS price_subtotal", table.consolidation_balance),
            SQL("%s * %s / %s AS price_total", table.price_subtotal, in_out_sign, table.move_id.invoice_currency_rate),
            SQL("%s * %s AS price_total_currency", table.price_total, in_out_sign),
            SQL(
                "-COALESCE((%s / NULLIF(%s, 0.0)) * %s, 0.0) AS price_average",
                table.consolidation_balance, quantity, in_out_sign,
            ),
            SQL(
                """
                CASE
                    WHEN %s NOT IN ('out_invoice', 'out_receipt', 'out_refund') THEN 0.0
                    WHEN %s = 'out_refund' THEN %s * (-%s + %s * COALESCE(%s, 0.0))
                    ELSE %s * (-%s - %s * COALESCE(%s, 0.0))
                END AS price_margin
                """,
                table.move_type,
                table.move_type, table.consolidation_rate, table.balance, quantity, table_with_company.product_id.standard_price,
                table.consolidation_rate, table.balance, quantity, table_with_company.product_id.standard_price,
            ),
            SQL(
                "-%s * %s * %s * COALESCE(%s, 0.0) AS inventory_value",
                table.consolidation_rate, quantity, in_out_sign, table_with_company.product_id.standard_price,
            ),
        ]

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
