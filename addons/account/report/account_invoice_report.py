# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api

from functools import lru_cache


class AccountInvoiceReport(models.Model):
    _name = "account.invoice.report"
    _description = "Invoices Statistics"
    _auto = False
    _rec_name = 'invoice_date'
    _order = 'invoice_date desc'

    # ==== Invoice fields ====
    move_id = fields.Many2one('account.move', readonly=True)
    name = fields.Char('Invoice #', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', string='Partner Company', help="Commercial Entity")
    country_id = fields.Many2one('res.country', string="Country")
    invoice_user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    type = fields.Selection([
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
    invoice_payment_state = fields.Selection(selection=[
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'paid')
    ], string='Payment Status', readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True)
    invoice_date = fields.Date(readonly=True, string="Invoice Date")
    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', readonly=True)
    invoice_partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account', readonly=True)
    nbr_lines = fields.Integer(string='Line Count', readonly=True)
    residual = fields.Float(string='Due Amount', readonly=True)
    amount_total = fields.Float(string='Total', readonly=True)

    # ==== Invoice line fields ====
    quantity = fields.Float(string='Product Quantity', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    invoice_date_due = fields.Date(string='Due Date', readonly=True)
    account_id = fields.Many2one('account.account', string='Revenue/Expense Account', readonly=True, domain=[('deprecated', '=', False)])
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', groups="analytic.group_analytic_accounting")
    price_subtotal = fields.Float(string='Untaxed Total', readonly=True)
    price_average = fields.Float(string='Average Price', readonly=True, group_operator="avg")

    _depends = {
        'account.move': [
            'name', 'state', 'type', 'partner_id', 'invoice_user_id', 'fiscal_position_id',
            'invoice_date', 'invoice_date_due', 'invoice_payment_term_id', 'invoice_partner_bank_id',
        ],
        'account.move.line': [
            'quantity', 'price_subtotal', 'amount_residual', 'balance', 'amount_currency',
            'move_id', 'product_id', 'product_uom_id', 'account_id', 'analytic_account_id',
            'journal_id', 'company_id', 'currency_id', 'partner_id',
        ],
        'product.product': ['product_tmpl_id'],
        'product.template': ['categ_id'],
        'uom.uom': ['category_id', 'factor', 'name', 'uom_type'],
        'res.currency.rate': ['currency_id', 'name'],
        'res.partner': ['country_id'],
    }

    @api.model
    def _select(self):
        return '''
            SELECT
                line.id,
                line.move_id,
                line.product_id,
                line.account_id,
                line.analytic_account_id,
                line.journal_id,
                line.company_id,
                line.company_currency_id                                    AS currency_id,
                line.partner_id AS commercial_partner_id,
                move.name,
                move.state,
                move.type,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.invoice_payment_state,
                move.invoice_date,
                move.invoice_date_due,
                move.invoice_payment_term_id,
                move.invoice_partner_bank_id,
                -line.balance * (move.amount_residual_signed / NULLIF(move.amount_total_signed, 0.0)) * (line.price_total / NULLIF(line.price_subtotal, 0.0))
                                                                            AS residual,
                -line.balance * (line.price_total / NULLIF(line.price_subtotal, 0.0))    AS amount_total,
                uom_template.id                                             AS product_uom_id,
                template.categ_id                                           AS product_categ_id,
                line.quantity / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0) * (CASE WHEN move.type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                                                                            AS quantity,
                -line.balance                                               AS price_subtotal,
                -line.balance / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0)
                                                                            AS price_average,
                COALESCE(partner.country_id, commercial_partner.country_id) AS country_id,
                1                                                           AS nbr_lines
        '''

    @api.model
    def _from(self):
        return '''
            FROM account_move_line line
                LEFT JOIN res_partner partner ON partner.id = line.partner_id
                LEFT JOIN product_product product ON product.id = line.product_id
                LEFT JOIN account_account account ON account.id = line.account_id
                LEFT JOIN account_account_type user_type ON user_type.id = account.user_type_id
                LEFT JOIN product_template template ON template.id = product.product_tmpl_id
                LEFT JOIN uom_uom uom_line ON uom_line.id = line.product_uom_id
                LEFT JOIN uom_uom uom_template ON uom_template.id = template.uom_id
                INNER JOIN account_move move ON move.id = line.move_id
                LEFT JOIN res_partner commercial_partner ON commercial_partner.id = move.commercial_partner_id
        '''

    @api.model
    def _where(self):
        return '''
            WHERE move.type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
                AND line.account_id IS NOT NULL
                AND NOT line.exclude_from_invoice_tab
        '''

    @api.model
    def _group_by(self):
        return '''
            GROUP BY
                line.id,
                line.move_id,
                line.product_id,
                line.account_id,
                line.analytic_account_id,
                line.journal_id,
                line.company_id,
                line.currency_id,
                line.partner_id,
                move.name,
                move.state,
                move.type,
                move.amount_residual_signed,
                move.amount_total_signed,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.invoice_payment_state,
                move.invoice_date,
                move.invoice_date_due,
                move.invoice_payment_term_id,
                move.invoice_partner_bank_id,
                uom_template.id,
                uom_line.factor,
                template.categ_id,
                COALESCE(partner.country_id, commercial_partner.country_id)
        '''

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
            CREATE OR REPLACE VIEW %s AS (
                %s %s %s %s
            )
        ''' % (
            self._table, self._select(), self._from(), self._where(), self._group_by()
        ))

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        @lru_cache(maxsize=32)  # cache to prevent a SQL query for each data point
        def get_rate(currency_id):
            return self.env['res.currency']._get_conversion_rate(
                self.env['res.currency'].browse(currency_id),
                self.env.company.currency_id,
                self.env.company,
                self._fields['invoice_date'].today()
            )

        # First we get the structure of the results. The results won't be correct in multi-currency,
        # but we need this result structure.
        # By adding 'ids:array_agg(id)' to the fields, we will be able to map the results of the
        # second step in the structure of the first step.
        result_ref = super(AccountInvoiceReport, self).read_group(
            domain, fields + ['ids:array_agg(id)'], groupby, offset, limit, orderby, lazy
        )

        # In mono-currency, the results are correct, so we don't need the second step.
        if len(self.env.companies.mapped('currency_id')) <= 1:
            return result_ref

        # Reset all fields needing recomputation.
        for res_ref in result_ref:
            for field in {'amount_total', 'price_average', 'price_subtotal', 'residual'} & set(res_ref):
                res_ref[field] = 0.0

        # Then we perform another read_group, but this time we group by 'currency_id'. This way, we
        # are able to convert in batch in the current company currency.
        # During the process, we fill in the result structure we got in the previous step. To make
        # the mapping, we use the aggregated ids.
        result = super(AccountInvoiceReport, self).read_group(
            domain, fields + ['ids:array_agg(id)'], set(groupby) | {'currency_id'}, offset, limit, orderby, lazy
        )
        for res in result:
            if res.get('currency_id') and self.env.company.currency_id.id != res['currency_id'][0]:
                for field in {'amount_total', 'price_average', 'price_subtotal', 'residual'} & set(res):
                    res[field] = self.env.company.currency_id.round((res[field] or 0.0) * get_rate(res['currency_id'][0]))
            # Since the size of result_ref should be resonable, it should be fine to loop inside a
            # loop.
            for res_ref in result_ref:
                if res.get('ids') and res_ref.get('ids') and set(res['ids']) <= set(res_ref['ids']):
                    for field in {'amount_total', 'price_subtotal', 'residual'} & set(res_ref):
                        res_ref[field] += res[field]
                    for field in {'price_average'} & set(res_ref):
                        res_ref[field] = (res_ref[field] + res[field]) / 2 if res_ref[field] else res[field]

        return result_ref


class ReportInvoiceWithPayment(models.AbstractModel):
    _name = 'report.account.report_invoice_with_payments'
    _description = 'Account report with payment lines'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': self.env['account.move'].browse(docids),
            'report_type': data.get('report_type') if data else '',
        }
