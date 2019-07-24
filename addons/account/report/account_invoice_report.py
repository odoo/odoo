# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api


class AccountInvoiceReport(models.Model):
    _name = "account.invoice.report"
    _description = "Invoices Statistics"
    _auto = False
    _rec_name = 'date'

    @api.multi
    @api.depends('currency_id', 'date', 'price_total', 'price_average', 'residual')
    def _compute_amounts_in_user_currency(self):
        """Compute the amounts in the currency of the user
        """
        user_currency_id = self.env.user.company_id.currency_id
        currency_rate_id = self.env['res.currency.rate'].search([
            ('rate', '=', 1),
            '|', ('company_id', '=', self.env.user.company_id.id), ('company_id', '=', False)], limit=1)
        base_currency_id = currency_rate_id.currency_id
        for record in self:
            date = record.date or fields.Date.today()
            company = record.company_id
            record.user_currency_price_total = base_currency_id._convert(record.price_total, user_currency_id, company, date)
            record.user_currency_price_average = base_currency_id._convert(record.price_average, user_currency_id, company, date)
            record.user_currency_residual = base_currency_id._convert(record.residual, user_currency_id, company, date)

    number = fields.Char('Invoice #', readonly=True)
    date = fields.Date(readonly=True, string="Invoice Date")
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_qty = fields.Float(string='Product Quantity', readonly=True)
    uom_name = fields.Char(string='Reference Unit of Measure', readonly=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term', readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', string='Partner Company', help="Commercial Entity")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    price_total = fields.Float(string='Untaxed Total', readonly=True)
    user_currency_price_total = fields.Float(string="Total Without Tax in Currency", compute='_compute_amounts_in_user_currency', digits=0)
    price_average = fields.Float(string='Average Price', readonly=True, group_operator="avg")
    user_currency_price_average = fields.Float(string="Average Price in Currency", compute='_compute_amounts_in_user_currency', digits=0)
    currency_rate = fields.Float(string='Currency Rate', readonly=True, group_operator="avg", groups="base.group_multi_currency")
    nbr = fields.Integer(string='Line Count', readonly=True)  # TDE FIXME master: rename into nbr_lines
    invoice_id = fields.Many2one('account.invoice', readonly=True)
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
        ], readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled')
        ], string='Invoice Status', readonly=True)
    date_due = fields.Date(string='Due Date', readonly=True)
    account_id = fields.Many2one('account.account', string='Receivable/Payable Account', readonly=True, domain=[('deprecated', '=', False)])
    account_line_id = fields.Many2one('account.account', string='Revenue/Expense Account', readonly=True, domain=[('deprecated', '=', False)])
    partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account', readonly=True)
    residual = fields.Float(string='Due Amount', readonly=True)
    user_currency_residual = fields.Float(string="Total Residual", compute='_compute_amounts_in_user_currency', digits=0)
    country_id = fields.Many2one('res.country', string="Partner Company's Country")
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', groups="analytic.group_analytic_accounting")
    amount_total = fields.Float(string='Total', readonly=True)

    _order = 'date desc'

    _depends = {
        'account.invoice': [
            'account_id', 'amount_total_company_signed', 'commercial_partner_id', 'company_id',
            'currency_id', 'date_due', 'date_invoice', 'fiscal_position_id',
            'journal_id', 'number', 'partner_bank_id', 'partner_id', 'payment_term_id',
            'residual', 'state', 'type', 'user_id',
        ],
        'account.invoice.line': [
            'account_id', 'invoice_id', 'price_subtotal', 'product_id',
            'quantity', 'uom_id', 'account_analytic_id',
        ],
        'product.product': ['product_tmpl_id'],
        'product.template': ['categ_id'],
        'uom.uom': ['category_id', 'factor', 'name', 'uom_type'],
        'res.currency.rate': ['currency_id', 'name'],
        'res.partner': ['country_id'],
    }

    def _select(self):
        select_str = """
            SELECT sub.id, sub.number, sub.date, sub.product_id, sub.partner_id, sub.country_id, sub.account_analytic_id,
                sub.payment_term_id, sub.uom_name, sub.currency_id, sub.journal_id,
                sub.fiscal_position_id, sub.user_id, sub.company_id, sub.nbr, sub.invoice_id, sub.type, sub.state,
                sub.categ_id, sub.date_due, sub.account_id, sub.account_line_id, sub.partner_bank_id,
                sub.product_qty, sub.price_total as price_total, sub.price_average as price_average, sub.amount_total / COALESCE(cr.rate, 1) as amount_total,
                COALESCE(cr.rate, 1) as currency_rate, sub.residual as residual, sub.commercial_partner_id as commercial_partner_id
        """
        return select_str

    def _sub_select(self):
        select_str = """
                SELECT ail.id AS id,
                    ai.date_invoice AS date,
                    ai.number as number,
                    ail.product_id, ai.partner_id, ai.payment_term_id, ail.account_analytic_id,
                    u2.name AS uom_name,
                    ai.currency_id, ai.journal_id, ai.fiscal_position_id, ai.user_id, ai.company_id,
                    1 AS nbr,
                    ai.id AS invoice_id, ai.type, ai.state, pt.categ_id, ai.date_due, ai.account_id, ail.account_id AS account_line_id,
                    ai.partner_bank_id,
                    SUM ((invoice_type.sign_qty * ail.quantity) / COALESCE(u.factor,1) * COALESCE(u2.factor,1)) AS product_qty,
                    SUM(ail.price_subtotal_signed * invoice_type.sign) AS price_total,
                    SUM(ail.price_total * invoice_type.sign_qty) AS amount_total,
                    SUM(ABS(ail.price_subtotal_signed)) / CASE
                            WHEN SUM(ail.quantity / COALESCE(u.factor,1) * COALESCE(u2.factor,1)) <> 0::numeric
                               THEN SUM(ail.quantity / COALESCE(u.factor,1) * COALESCE(u2.factor,1))
                               ELSE 1::numeric
                            END AS price_average,
                    ai.residual_company_signed / (SELECT count(*) FROM account_invoice_line l where invoice_id = ai.id) *
                    count(*) * invoice_type.sign AS residual,
                    ai.commercial_partner_id as commercial_partner_id,
                    coalesce(partner.country_id, partner_ai.country_id) AS country_id
        """
        return select_str

    def _from(self):
        from_str = """
                FROM account_invoice_line ail
                JOIN account_invoice ai ON ai.id = ail.invoice_id
                JOIN res_partner partner ON ai.commercial_partner_id = partner.id
                JOIN res_partner partner_ai ON ai.partner_id = partner_ai.id
                LEFT JOIN product_product pr ON pr.id = ail.product_id
                left JOIN product_template pt ON pt.id = pr.product_tmpl_id
                LEFT JOIN uom_uom u ON u.id = ail.uom_id
                LEFT JOIN uom_uom u2 ON u2.id = pt.uom_id
                JOIN (
                    -- Temporary table to decide if the qty should be added or retrieved (Invoice vs Credit Note)
                    SELECT id,(CASE
                         WHEN ai.type::text = ANY (ARRAY['in_refund'::character varying::text, 'in_invoice'::character varying::text])
                            THEN -1
                            ELSE 1
                        END) AS sign,(CASE
                         WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                            THEN -1
                            ELSE 1
                        END) AS sign_qty
                    FROM account_invoice ai
                ) AS invoice_type ON invoice_type.id = ai.id
        """
        return from_str

    def _group_by(self):
        group_by_str = """
                GROUP BY ail.id, ail.product_id, ail.account_analytic_id, ai.date_invoice, ai.id,
                    ai.partner_id, ai.payment_term_id, u2.name, u2.id, ai.currency_id, ai.journal_id,
                    ai.fiscal_position_id, ai.user_id, ai.company_id, ai.id, ai.type, invoice_type.sign, ai.state, pt.categ_id,
                    ai.date_due, ai.account_id, ail.account_id, ai.partner_bank_id, ai.residual_company_signed,
                    ai.amount_total_company_signed, ai.commercial_partner_id, coalesce(partner.country_id, partner_ai.country_id)
        """
        return group_by_str

    @api.model_cr
    def init(self):
        # self._table = account_invoice_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            WITH currency_rate AS (%s)
            %s
            FROM (
                %s %s WHERE ail.account_id IS NOT NULL %s
            ) AS sub
            LEFT JOIN currency_rate cr ON
                (cr.currency_id = sub.currency_id AND
                 cr.company_id = sub.company_id AND
                 cr.date_start <= COALESCE(sub.date, NOW()) AND
                 (cr.date_end IS NULL OR cr.date_end > COALESCE(sub.date, NOW())))
        )""" % (
                    self._table, self.env['res.currency']._select_companies_rates(),
                    self._select(), self._sub_select(), self._from(), self._group_by()))


class ReportInvoiceWithPayment(models.AbstractModel):
    _name = 'report.account.report_invoice_with_payments'
    _description = 'Account report with payment lines'

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('account.report_invoice_with_payments')
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(docids),
            'report_type': data.get('report_type') if data else '',
        }
