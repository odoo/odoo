# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticDefault(models.Model):
    _name = "account.analytic.default"
    _description = "Analytic Distribution"
    _rec_name = "analytic_id"
    _order = "sequence"

    sequence = fields.Integer(string='Sequence', help="Gives the sequence order when displaying a list of analytic distribution")
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade', help="Select a product which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this product, it will automatically take this as an analytic account)")
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade', help="Select a partner which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)")
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', help="Select a user which will use analytic account specified in analytic default.")
    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade', help="Select a company which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this company, it will automatically take this as an analytic account)")
    date_start = fields.Date(string='Start Date', help="Default start date for this Analytic Account.")
    date_stop = fields.Date(string='End Date', help="Default end date for this Analytic Account.")

    @api.model
    def account_get(self, product_id=None, partner_id=None, user_id=None, date=None, company_id=None):
        domain = []
        if product_id:
            domain += ['|', ('product_id', '=', product_id)]
        domain += [('product_id', '=', False)]
        if partner_id:
            domain += ['|', ('partner_id', '=', partner_id)]
        domain += [('partner_id', '=', False)]
        if company_id:
            domain += ['|', ('company_id', '=', company_id)]
        domain += [('company_id', '=', False)]
        if user_id:
            domain += ['|', ('user_id', '=', user_id)]
        domain += [('user_id', '=', False)]
        if date:
            domain += ['|', ('date_start', '<=', date), ('date_start', '=', False)]
            domain += ['|', ('date_stop', '>=', date), ('date_stop', '=', False)]
        best_index = -1
        res = self.env['account.analytic.default']
        for rec in self.search(domain):
            index = 0
            if rec.product_id: index += 1
            if rec.partner_id: index += 1
            if rec.company_id: index += 1
            if rec.user_id: index += 1
            if rec.date_start: index += 1
            if rec.date_stop: index += 1
            if index > best_index:
                res = rec
                best_index = index
        return res


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        rec = self.env['account.analytic.default'].account_get(self.product_id.id, self.invoice_id.partner_id.id, self.env.uid,
                                                               fields.Date.today(), company_id=self.company_id.id)
        self.account_analytic_id = rec.analytic_id.id
        return res

    def _set_additional_fields(self, invoice):
        rec = self.env['account.analytic.default'].account_get(self.product_id.id, self.invoice_id.partner_id.id, self.env.uid,
                                                               fields.Date.today(), company_id=self.company_id.id)
        self.account_analytic_id = rec.analytic_id.id
        super(AccountInvoiceLine, self)._set_additional_fields(invoice)
