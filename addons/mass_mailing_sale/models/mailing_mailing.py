# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class MassMailing(models.Model):
    _name = 'mailing.mailing'
    _inherit = 'mailing.mailing'

    sale_quotation_count = fields.Integer('Quotation Count', groups='sales_team.group_sale_salesman', compute='_compute_sale_quotation_count')
    sale_invoiced_amount = fields.Integer('Invoiced Amount', groups='sales_team.group_sale_salesman', compute='_compute_sale_invoiced_amount')

    @api.depends('mailing_domain')
    def _compute_sale_quotation_count(self):
        has_so_access = self.env['sale.order'].check_access_rights('read', raise_exception=False)
        for mass_mailing in self:
            mass_mailing.sale_quotation_count = self.env['sale.order'].search_count(mass_mailing._get_sale_utm_domain()) if has_so_access else 0

    @api.depends('mailing_domain')
    def _compute_sale_invoiced_amount(self):
        for mass_mailing in self:
            if self.user_has_groups('sales_team.group_sale_salesman') and self.user_has_groups('account.group_account_invoice'):
                domain = mass_mailing._get_sale_utm_domain() + [('state', 'not in', ['draft', 'cancel'])]
                moves = self.env['account.move'].search_read(domain, ['amount_untaxed_signed'])
                mass_mailing.sale_invoiced_amount = sum(i['amount_untaxed_signed'] for i in moves)
            else:
                mass_mailing.sale_invoiced_amount = 0

    def action_redirect_to_quotations(self):
        action = self.env.ref('sale.action_quotations_with_onboarding').read()[0]
        action['domain'] = self._get_sale_utm_domain()
        action['context'] = {'create': False}
        return action

    def action_redirect_to_invoiced(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        moves = self.env['account.move'].search(self._get_sale_utm_domain())
        action['context'] = {
            'create': False,
            'edit': False,
            'view_no_maturity': True
        }
        action['domain'] = [
            ('id', 'in', moves.ids),
            ('type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')),
            ('state', 'not in', ['draft', 'cancel'])
        ]
        action['context'] = {'create': False}
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
