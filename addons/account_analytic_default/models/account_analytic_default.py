# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticDefault(models.Model):
    _name = "account.analytic.default"
    _description = "Analytic Distribution"
    _rec_name = "analytic_id"
    _order = "sequence"

    sequence = fields.Integer(string='Sequence', help="Gives the sequence order when displaying a list of analytic distribution")
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade', help="Select a product which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this product, it will automatically take this as an analytic account)")
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade', help="Select a partner which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)")
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', help="Select a user which will use analytic account specified in analytic default.")
    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade', help="Select a company which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this company, it will automatically take this as an analytic account)")
    date_start = fields.Date(string='Start Date', help="Default start date for this Analytic Account.")
    date_stop = fields.Date(string='End Date', help="Default end date for this Analytic Account.")

    @api.constrains('analytic_id', 'analytic_tag_ids')
    def _check_account_or_tags(self):
        if any(not default.analytic_id and not default.analytic_tag_ids for default in self):
            raise ValidationError(_('An analytic default requires at least an analytic account or an analytic tag.'))

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

    @api.model
    def default_get(self, fields_list):
        defaults = super(AccountInvoiceLine, self).default_get(fields_list)
        if set(['account_analytic_id', 'analytic_tag_ids']) & set(fields_list):
            rec = self.env['account.analytic.default'].account_get(
                self.product_id.id,
                self.invoice_id.commercial_partner_id.id,
                self.invoice_id.user_id.id or self.env.uid,
                fields.Date.today(),
                company_id=self.company_id.id
            )
            if rec:
                if 'account_analytic_id' in fields_list:
                    defaults.update({
                        'account_analytic_id': rec.analytic_id.id,
                    })
                if 'analytic_tag_ids' in fields_list:
                    defaults.update({
                        'analytic_tag_ids': rec.analytic_tag_ids.ids,
                    })
        return defaults

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        rec = self.env['account.analytic.default'].account_get(
            self.product_id.id,
            self.invoice_id.commercial_partner_id.id,
            self.invoice_id.user_id.id or self.env.uid,
            fields.Date.today(),
            company_id=self.company_id.id
        )
        if rec:
            self.account_analytic_id = rec.analytic_id.id
            self.analytic_tag_ids = rec.analytic_tag_ids.ids
        return res

    def _set_additional_fields(self, invoice):
        if not self.account_analytic_id or not self.analytic_tag_ids:
            rec = self.env['account.analytic.default'].account_get(
                self.product_id.id,
                self.invoice_id.commercial_partner_id.id,
                self.invoice_id.user_id.id or self.env.uid,
                fields.Date.today(),
                company_id=invoice.company_id.id
            )
            if rec:
                if self.account_analytic_id:
                    self.account_analytic_id = rec.analytic_id.id
                if self.analytic_tag_ids:
                    self.analytic_tag_ids = rec.analytic_tag_ids.ids
        super(AccountInvoiceLine, self)._set_additional_fields(invoice)
