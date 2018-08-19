# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class MassMailing(models.Model):
    _name = 'mail.mass_mailing'
    _inherit = 'mail.mass_mailing'

    sale_quotation_count = fields.Integer('Quotation Count', compute='_compute_sale_quotation_count')
    sale_invoiced_amount = fields.Integer('Invoiced Amount', compute='_compute_sale_invoiced_amount')

    @api.depends('mailing_domain')
    def _compute_sale_quotation_count(self):
        for mass_mailing in self:
            if mass_mailing.mailing_model_name != 'sale.order':
                mass_mailing.sale_quotation_count = 0
            else:
                mass_mailing.sale_quotation_count = self.env['sale.order'].search_count(self._get_sale_utm_domain())

    @api.depends('mailing_domain')
    def _compute_sale_invoiced_amount(self):
        for mass_mailing in self:
            if mass_mailing.mailing_model_name != 'sale.order':
                mass_mailing.sale_invoiced_amount = 0
            else:
                invoices = self.env['sale.order'].search(self._get_sale_utm_domain()).mapped('invoice_ids')
                res = self.env['account.invoice.report'].search_read([('invoice_id', 'in', invoices.ids)], ['user_currency_price_total'])
                mass_mailing.sale_invoiced_amount = sum(r['user_currency_price_total'] for r in res)

    @api.multi
    def action_redirect_to_quotations(self):
        action = self.env.ref('sale.action_quotations_with_onboarding').read()[0]
        action['domain'] = self._get_sale_utm_domain()
        action['context'] = {'default_type': 'lead'}
        return action

    @api.multi
    def action_redirect_to_invoiced(self):
        action = self.env.ref('account.action_invoice_refund_out_tree').read()[0]
        invoices = self.env['sale.order'].search(self._get_sale_utm_domain()).mapped('invoice_ids')
        action['domain'] = [
            ('id', 'in', invoices.ids),
            ('type', 'in', ['out_invoice', 'out_refund']),
            ('state', 'not in', ['draft', 'cancel'])
        ]
        return action

    def _get_sale_utm_domain(self):
        res = []
        if self.campaign_id:
            res.append(('campaign_id', '=', self.campaign_id.id))
        if self.source_id:
            res.append(('source_id', '=', self.source_id.id))
        if self.medium_id:
            res.append(('medium_id', '=', self.medium_id.id))
        if not res:
            res.append(('1', '=', '0'))
        return res
