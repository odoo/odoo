# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_move_create(self):
        result = super(AccountInvoice, self).action_move_create()
        for inv in self:
            inv.invoice_line_ids.asset_create()
        return result


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    asset_category_id = fields.Many2one('account.asset.category', string='Asset Category')
    asset_start_date = fields.Date(string='Asset End Date', compute='_get_asset_date', readonly=True, store=True)
    asset_end_date = fields.Date(string='Asset Start Date', compute='_get_asset_date', readonly=True, store=True)
    asset_mrr = fields.Float(string='Monthly Recurring Revenue', compute='_get_asset_date', readonly=True, digits=dp.get_precision('Account'), store=True)

    @api.one
    @api.depends('asset_category_id', 'invoice_id.date_invoice')
    def _get_asset_date(self):
        self.asset_mrr = 0
        self.asset_start_date = False
        self.asset_end_date = False
        cat = self.asset_category_id
        if cat:
            months = cat.method_number * cat.method_period
            if self.invoice_id.type in ['out_invoice', 'out_refund']:
                self.asset_mrr = self.price_subtotal_signed / months
            if self.invoice_id.date_invoice:
                start_date = datetime.strptime(self.invoice_id.date_invoice, DF).replace(day=1)
                end_date = (start_date + relativedelta(months=months, days=-1))
                self.asset_start_date = start_date.strftime(DF)
                self.asset_end_date = end_date.strftime(DF)

    @api.one
    def asset_create(self):
        if self.asset_category_id and self.asset_category_id.method_number > 1:
            vals = {
                'name': self.name,
                'code': self.invoice_id.number or False,
                'category_id': self.asset_category_id.id,
                'value': self.price_subtotal,
                'partner_id': self.invoice_id.partner_id.id,
                'company_id': self.invoice_id.company_id.id,
                'currency_id': self.invoice_id.currency_id.id,
                'date': self.asset_start_date or self.invoice_id.date_invoice,
                'invoice_id': self.invoice_id.id,
            }
            changed_vals = self.env['account.asset.asset'].onchange_category_id_values(vals['category_id'])
            vals.update(changed_vals['value'])
            asset = self.env['account.asset.asset'].create(vals)
            if self.asset_category_id.open_asset:
                asset.validate()
        return True

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            if self.invoice_id.type == 'out_invoice':
                self.asset_category_id = self.product_id.product_tmpl_id.deferred_revenue_category_id
            elif self.invoice_id.type == 'in_invoice':
                self.asset_category_id = self.product_id.product_tmpl_id.asset_category_id

    def _set_additional_fields(self, invoice):
        if not self.asset_category_id:
            if invoice.type == 'out_invoice':
                self.asset_category_id = self.product_id.product_tmpl_id.deferred_revenue_category_id.id
            elif invoice.type == 'in_invoice':
                self.asset_category_id = self.product_id.product_tmpl_id.asset_category_id.id
        super(AccountInvoiceLine, self)._set_additional_fields(invoice)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    asset_category_id = fields.Many2one('account.asset.category', string='Asset Type', ondelete="restrict")
    deferred_revenue_category_id = fields.Many2one('account.asset.category', string='Deferred Revenue Type', ondelete="restrict")
