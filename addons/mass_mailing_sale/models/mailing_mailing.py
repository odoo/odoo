# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo import api, fields, models, _, tools
from odoo.osv import expression


class MassMailing(models.Model):
    _name = 'mailing.mailing'
    _inherit = 'mailing.mailing'

    sale_quotation_count = fields.Integer('Quotation Count', compute='_compute_sale_quotation_count')
    sale_invoiced_amount = fields.Integer('Invoiced Amount', compute='_compute_sale_invoiced_amount')

    @api.depends('mailing_domain')
    def _compute_sale_quotation_count(self):
        quotation_data = self.env['sale.order'].sudo()._read_group(
            [('source_id', 'in', self.source_id.ids), ('order_line', '!=', False)],
            ['source_id'], ['source_id'],
        )
        mapped_data = {datum['source_id'][0]: datum['source_id_count'] for datum in quotation_data}
        for mass_mailing in self:
            mass_mailing.sale_quotation_count = mapped_data.get(mass_mailing.source_id.id, 0)

    @api.depends('mailing_domain')
    def _compute_sale_invoiced_amount(self):
        domain = expression.AND([
            [('source_id', 'in', self.source_id.ids)],
            [('state', 'not in', ['draft', 'cancel'])]
        ])
        moves_data = self.env['account.move'].sudo()._read_group(
            domain, ['source_id', 'amount_untaxed_signed'], ['source_id'],
        )
        mapped_data = {datum['source_id'][0]: datum['amount_untaxed_signed'] for datum in moves_data}
        for mass_mailing in self:
            mass_mailing.sale_invoiced_amount = mapped_data.get(mass_mailing.source_id.id, 0)

    def action_redirect_to_quotations(self):
        helper_header = _("No Quotations yet!")
        helper_message = _("Quotations will appear here once your customers add "
                           "products to their Carts or when your sales reps assign this mailing.")
        return {
            'context': {
                'create': False,
                'search_default_group_by_date_day': True,
                'sale_report_view_hide_date': True,
            },
            'domain': [('source_id', '=', self.source_id.id)],
            'help': Markup('<p class="o_view_nocontent_smiling_face">%s</p><p>%s</p>') % (
                helper_header, helper_message,
            ),
            'name': _("Sales Analysis"),
            'res_model': 'sale.report',
            'type': 'ir.actions.act_window',
            'view_mode': 'graph,pivot,tree,form',
        }

    def action_redirect_to_invoiced(self):
        domain = expression.AND([
            [('source_id', '=', self.source_id.id)],
            [('state', 'not in', ['draft', 'cancel'])]
        ])
        moves = self.env['account.move'].search(domain)
        helper_header = _("No Revenues yet!")
        helper_message = _("Revenues will appear here once orders are turned into invoices.")
        return {
            'context': {
                'create': False,
                'edit': False,
                'view_no_maturity': True,
                'search_default_group_by_invoice_date_week': True,
                'invoice_report_view_hide_invoice_date': True,
            },
            'domain': [('move_id', 'in', moves.ids)],
            'help': Markup('<p class="o_view_nocontent_smiling_face">%s</p><p>%s</p>') % (
                helper_header, helper_message,
            ),
            'name': _("Invoices Analysis"),
            'res_model': 'account.invoice.report',
            'type': 'ir.actions.act_window',
            'view_mode': 'graph,pivot,tree,form',
        }

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
