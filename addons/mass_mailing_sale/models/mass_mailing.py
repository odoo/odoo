# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class MassMailing(models.Model):
    _name = 'mail.mass_mailing'
    _inherit = 'mail.mass_mailing'

    sale_quotation_count = fields.Integer('Quotation Count', groups='sales_team.group_sale_salesman', compute='_compute_sale_quotation_count')
    sale_invoiced_amount = fields.Integer('Invoiced Amount', groups='sales_team.group_sale_salesman', compute='_compute_sale_invoiced_amount')

    @api.depends('mailing_domain')
    def _compute_sale_quotation_count(self):
        has_so_access = self.env['sale.order'].check_access_rights('read', raise_exception=False)
        for mass_mailing in self:
            mass_mailing.sale_quotation_count = self.env['sale.order'].search_count(self._get_sale_utm_domain()) if has_so_access else 0

    @api.depends('mailing_domain')
    def _compute_sale_invoiced_amount(self):
        has_so_access = self.env['sale.order'].check_access_rights('read', raise_exception=False)
        has_invoice_report_access = self.env['account.invoice.report'].check_access_rights('read', raise_exception=False)
        for mass_mailing in self:
            if has_so_access and has_invoice_report_access:
                invoices = self.env['sale.order'].search(self._get_sale_utm_domain()).mapped('invoice_ids')
                res = self.env['account.invoice.report'].search_read(
                    [('invoice_id', 'in', invoices.ids), ('state', 'not in', ['draft', 'cancel'])],
                    ['price_subtotal']
                )
                mass_mailing.sale_invoiced_amount = sum(r['price_subtotal'] for r in res)
            else:
                mass_mailing.sale_invoiced_amount = 0

    def action_redirect_to_quotations(self):
        action = self.env.ref('sale.action_quotations_with_onboarding').read()[0]
        action['domain'] = self._get_sale_utm_domain()
        action['context'] = {'default_type': 'lead'}
        return action

    def action_redirect_to_invoiced(self):
        action = self.env.ref('account.view_move_form').read()[0]
        invoices = self.env['sale.order'].search(self._get_sale_utm_domain()).mapped('invoice_ids')
        action['domain'] = [
            ('id', 'in', invoices.ids),
            ('type', 'in', ('out_invoice', 'out_refund')),
            ('type', '=', 'posted'),
            ('partner_id', 'child_of', self.id),
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
            res.append((0, '=', 1))
        return res
