# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _, tools
from odoo.osv import expression


class MassMailing(models.Model):
    _name = 'mailing.mailing'
    _inherit = 'mailing.mailing'

    sale_quotation_count = fields.Integer('Quotation Count', groups='sales_team.group_sale_salesman', compute='_compute_sale_quotation_count')
    sale_invoiced_amount = fields.Integer('Invoiced Amount', groups='sales_team.group_sale_salesman', compute='_compute_sale_invoiced_amount')

    @api.depends('mailing_domain')
    def _compute_sale_quotation_count(self):
        has_so_access = self.env['sale.order'].check_access_rights('read', raise_exception=False)
        if not has_so_access:
            self.sale_quotation_count = 0
            return
        for mass_mailing in self:
            mass_mailing.sale_quotation_count = self.env['sale.order'].search_count(mass_mailing._get_sale_utm_domain())

    @api.depends('mailing_domain')
    def _compute_sale_invoiced_amount(self):
        if not self.user_has_groups('sales_team.group_sale_salesman') or not self.user_has_groups('account.group_account_invoice'):
            self.sale_invoiced_amount = 0
            return
        for mass_mailing in self:
            domain = expression.AND([
                mass_mailing._get_sale_utm_domain(),
                [('state', 'not in', ['draft', 'cancel'])]
            ])
            moves = self.env['account.move'].search_read(domain, ['amount_untaxed_signed'])
            mass_mailing.sale_invoiced_amount = sum(i['amount_untaxed_signed'] for i in moves)

    def action_redirect_to_quotations(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        action['domain'] = self._get_sale_utm_domain()
        action['context'] = {'create': False}
        return action

    def action_redirect_to_invoiced(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        moves = self.env['account.move'].search(self._get_sale_utm_domain())
        action['context'] = {
            'create': False,
            'edit': False,
            'view_no_maturity': True
        }
        action['domain'] = [
            ('id', 'in', moves.ids),
            ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')),
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

    def _prepare_statistics_email_values(self):
        self.ensure_one()
        values = super(MassMailing, self)._prepare_statistics_email_values()
        if not self.user_id:
            return values

        self_with_company = self.with_company(self.user_id.company_id)
        currency = self.user_id.company_id.currency_id
        formated_amount = tools.format_decimalized_amount(self_with_company.sale_invoiced_amount, currency)

        values['kpi_data'][1]['kpi_col2'] = {
            'value': self.sale_quotation_count,
            'col_subtitle': _('QUOTATIONS'),
        }
        values['kpi_data'][1]['kpi_col3'] = {
            'value': formated_amount,
            'col_subtitle': _('INVOICED'),
        }
        values['kpi_data'][1]['kpi_name'] = 'sale'
        return values
