# -*- coding:utf-8 -*-
#az Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class L10nInPaymentReport(models.AbstractModel):
    _name = "l10n_in.payment.report"
    _description = "Indian accounting payment report"

    account_move_id = fields.Many2one('account.move', string="Account Move")
    payment_id = fields.Many2one('account.payment', string='Payment')
    currency_id = fields.Many2one('res.currency', string="Currency")
    amount = fields.Float(string="Amount")
    payment_amount = fields.Float(string="Payment Amount")
    partner_id = fields.Many2one('res.partner', string="Customer")
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type')
    journal_id = fields.Many2one('account.journal', string="Journal")
    company_id = fields.Many2one(related="journal_id.company_id", string="Company")
    place_of_supply = fields.Char(string="Place of Supply")
    supply_type = fields.Char(string="Supply Type")

    l10n_in_tax_id = fields.Many2one('account.tax', string="Tax")
    tax_rate = fields.Float(string="Rate")
    igst_amount = fields.Float(compute="_compute_tax_amount", string="IGST amount")
    cgst_amount = fields.Float(compute="_compute_tax_amount", string="CGST amount")
    sgst_amount = fields.Float(compute="_compute_tax_amount", string="SGST amount")
    cess_amount = fields.Float(compute="_compute_tax_amount", string="CESS amount")
    gross_amount = fields.Float(compute="_compute_tax_amount", string="Gross advance")

    def _compute_l10n_in_tax(self, taxes, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        """common method to compute gst tax amount base on tax group"""
        res = {'igst_amount': 0.0, 'sgst_amount': 0.0, 'cgst_amount': 0.0, 'cess_amount': 0.0}
        AccountTag = self.env['account.account.tag']
        tax_report_line_igst = self.env.ref('l10n_in.tax_report_line_igst', False)
        tax_report_line_cgst = self.env.ref('l10n_in.tax_report_line_cgst', False)
        tax_report_line_sgst = self.env.ref('l10n_in.tax_report_line_sgst', False)
        tax_report_line_cess = self.env.ref('l10n_in.tax_report_line_cess', False)
        filter_tax = taxes.filtered(lambda t: t.type_tax_use != 'none')
        tax_compute = filter_tax.compute_all(price_unit, currency=currency, quantity=quantity, product=product, partner=partner)
        for tax_data in tax_compute['taxes']:
            tax_report_lines = AccountTag.browse(tax_data['tag_ids'][0][2]).mapped('tax_report_line_ids')
            if tax_report_line_sgst in tax_report_lines:
                res['sgst_amount'] += tax_data['amount']
            if tax_report_line_cgst in tax_report_lines:
                res['cgst_amount'] += tax_data['amount']
            if tax_report_line_igst in tax_report_lines:
                res['igst_amount'] += tax_data['amount']
            if tax_report_line_cess in tax_report_lines:
                res['cess_amount'] += tax_data['amount']
        res.update(tax_compute)
        return res

    #TO BE OVERWRITTEN
    @api.depends('currency_id')
    def _compute_tax_amount(self):
        """Calculate tax amount base on default tax set in company"""

    def _select(self):
        return """SELECT aml.id AS id,
            aml.move_id as account_move_id,
            ap.id AS payment_id,
            ap.payment_type,
            tax.id as l10n_in_tax_id,
            tax.amount AS tax_rate,
            am.partner_id,
            am.amount_total AS payment_amount,
            ap.journal_id,
            aml.currency_id,
            (CASE WHEN ps.l10n_in_tin IS NOT NULL
                THEN concat(ps.l10n_in_tin,'-',ps.name)
                WHEN p.id IS NULL and cps.l10n_in_tin IS NOT NULL
                THEN concat(cps.l10n_in_tin,'-',cps.name)
                ELSE ''
                END) AS place_of_supply,
            (CASE WHEN ps.id = cp.state_id or p.id IS NULL
                THEN 'Intra State'
                WHEN ps.id != cp.state_id and p.id IS NOT NULL
                THEN 'Inter State'
                END) AS supply_type"""

    def _from(self):
        return """FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_payment ap ON ap.id = aml.payment_id
            JOIN account_account AS ac ON ac.id = aml.account_id
            JOIN account_journal AS aj ON aj.id = am.journal_id
            JOIN res_company AS c ON c.id = aj.company_id
            JOIN account_tax AS tax ON tax.id = (
                CASE WHEN ap.payment_type = 'inbound'
                    THEN c.account_sale_tax_id
                    ELSE c.account_purchase_tax_id END)
            JOIN res_partner p ON p.id = aml.partner_id
            LEFT JOIN res_country_state ps ON ps.id = p.state_id
            LEFT JOIN res_partner cp ON cp.id = c.partner_id
            LEFT JOIN res_country_state cps ON cps.id = cp.state_id
            """

    def _where(self):
        return """WHERE aml.payment_id IS NOT NULL
            AND tax.tax_group_id in (SELECT res_id FROM ir_model_data WHERE module='l10n_in' AND name in ('igst_group','gst_group'))
            AND ac.internal_type IN ('receivable', 'payable') AND am.state = 'posted'"""

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (
            %s %s %s)""" % (self._table, self._select(), self._from(), self._where()))


class AdvancesPaymentReport(models.Model):
    _name = "l10n_in.advances.payment.report"
    _inherit = 'l10n_in.payment.report'
    _description = "Advances Payment Analysis"
    _auto = False

    date = fields.Date(string="Payment Date")
    reconcile_amount = fields.Float(string="Reconcile amount in Payment month")

    @api.depends('payment_amount', 'reconcile_amount', 'currency_id')
    def _compute_tax_amount(self):
        """Calculate tax amount base on default tax set in company"""
        account_move_line = self.env['account.move.line']
        for record in self:
            base_amount = record.payment_amount - record.reconcile_amount
            taxes_data = self._compute_l10n_in_tax(
                taxes=record.l10n_in_tax_id,
                price_unit=base_amount,
                currency=record.currency_id or None,
                quantity=1,
                partner=record.partner_id or None)
            record.igst_amount = taxes_data['igst_amount']
            record.cgst_amount = taxes_data['cgst_amount']
            record.sgst_amount = taxes_data['sgst_amount']
            record.cess_amount = taxes_data['cess_amount']
            record.gross_amount = taxes_data['total_excluded']

    def _select(self):
        select_str = super(AdvancesPaymentReport, self)._select()
        select_str += """,
            ap.payment_date as date,
            (SELECT sum(amount) FROM account_partial_reconcile AS apr
                WHERE (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                AND (to_char(apr.max_date, 'MM-YYYY') = to_char(aml.date_maturity, 'MM-YYYY'))
            ) AS reconcile_amount,
            (am.amount_total - (SELECT (CASE WHEN SUM(amount) IS NULL THEN 0 ELSE SUM(amount) END) FROM account_partial_reconcile AS apr
                WHERE (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                AND (to_char(apr.max_date, 'MM-YYYY') = to_char(aml.date_maturity, 'MM-YYYY'))
            )) AS amount"""
        return select_str


class L10nInAdvancesPaymentAdjustmentReport(models.Model):
    _name = "l10n_in.advances.payment.adjustment.report"
    _inherit = 'l10n_in.payment.report'
    _description = "Advances Payment Adjustment Analysis"
    _auto = False

    date = fields.Date('Reconcile Date')

    @api.depends('amount', 'currency_id', 'partner_id')
    def _compute_tax_amount(self):
        account_move_line = self.env['account.move.line']
        for record in self:
            taxes_data = self._compute_l10n_in_tax(
                taxes=record.l10n_in_tax_id,
                price_unit=record.amount,
                currency=record.currency_id or None,
                quantity=1,
                partner=record.partner_id or None)
            record.igst_amount = taxes_data['igst_amount']
            record.cgst_amount = taxes_data['cgst_amount']
            record.sgst_amount = taxes_data['sgst_amount']
            record.cess_amount = taxes_data['cess_amount']
            record.gross_amount = taxes_data['total_excluded']

    def _select(self):
        select_str = super(L10nInAdvancesPaymentAdjustmentReport, self)._select()
        select_str += """,
            apr.max_date AS date,
            apr.amount AS amount
            """
        return select_str

    def _from(self):
        from_str = super(L10nInAdvancesPaymentAdjustmentReport, self)._from()
        from_str += """
            JOIN account_partial_reconcile apr ON apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id
            """
        return from_str

    def _where(self):
        where_str = super(L10nInAdvancesPaymentAdjustmentReport, self)._where()
        where_str += """
            AND (apr.max_date > aml.date_maturity)
        """
        return where_str
