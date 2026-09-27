# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo import api, fields, models, _, tools
from odoo.fields import Domain
from odoo.tools import SQL


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    sale_quotation_count = fields.Integer('Quotation Count', compute='_compute_sale_quotation_count')
    sale_invoiced_amount = fields.Monetary('Invoiced Amount', compute='_compute_sale_invoiced_amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id', compute_sql="_compute_sql_currency_id", compute_sudo=True)

    @api.depends_context('company')
    def _compute_currency_id(self):
        self.currency_id = self.env.company.currency_id

    def _compute_sql_currency_id(self, table):
        return SQL("%s", self.env.company.currency_id.id)

    @api.depends('mailing_domain')
    def _compute_sale_quotation_count(self):
        quotation_data = self.env['sale.order'].sudo()._read_group(
            [('utm_reference', 'in', [f'{mailing._name},{mailing.id}' for mailing in self]), ('state', '!=', 'cancel')],
            ['utm_reference'], ['__count'],
        )
        mapped_data = dict(quotation_data)
        for mass_mailing in self:
            mass_mailing.sale_quotation_count = mapped_data.get(
                f'{mass_mailing._name},{mass_mailing.id}',
                0,
            )

    @api.depends('mailing_domain')
    def _compute_sale_invoiced_amount(self):
        if self.ids:
            query_res = self.env.execute_query(SQL(
                """SELECT move.utm_reference, SUM(move.amount_total_signed * COALESCE(currency_rate.rate, 1))
                     FROM account_move move
                     /* To use the exchange rate effective at the creation of the invoice. */
                     LEFT JOIN LATERAL (
                         SELECT rate
                           FROM res_currency_rate
                          WHERE company_id = move.company_id
                            AND currency_id = %(currency_id)s
                            AND name < move.date
                          ORDER BY name DESC
                          LIMIT 1
                     ) currency_rate
                       ON TRUE
                    WHERE move.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
                      AND move.state NOT IN ('draft', 'cancel')
                      AND move.utm_reference IN %(utm_references)s
                    GROUP BY move.utm_reference""",
                currency_id=self.env.company.currency_id.id,
                utm_references=tuple(f'{mass_mailing._name},{mass_mailing.id}' for mass_mailing in self)
            ))
            mapped_data = dict(query_res)
        else:
            mapped_data = {}

        for mass_mailing in self:
            mass_mailing.sale_invoiced_amount = mapped_data.get(
                f'{mass_mailing._name},{mass_mailing.id}',
                0,
            )

    def action_redirect_to_quotations(self):
        helper_header = _("No Quotations yet!")
        helper_message = _("Quotations will appear here once your customers add "
                           "products to their Carts or when your sales reps assign this mailing.")
        return {
            'context': {
                'create': False,
                'search_default_filter_not_cancelled': True,
                'search_default_group_by_date_day': True,
                'sale_report_view_hide_date': True,
            },
            'domain': [('utm_reference', 'in', [f'{mailing._name},{mailing.id}' for mailing in self])],
            'help': Markup('<p class="o_view_nocontent_smiling_face">%s</p><p>%s</p>') % (
                helper_header, helper_message,
            ),
            'name': _("Sales Analysis"),
            'res_model': 'sale.report',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,pivot,graph,form',
        }

    def action_redirect_to_invoiced(self):
        domain = Domain.AND([
            [('utm_reference', 'in', [f'{mailing._name},{mailing.id}' for mailing in self])],
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
            'view_mode': 'list,pivot,graph,form',
        }

    def _prepare_statistics_email_values(self):
        self.ensure_one()
        values = super()._prepare_statistics_email_values()
        if not self.user_id:
            return values

        self_with_company = self.with_company(self.user_id.company_id)
        currency = self.user_id.company_id.currency_id
        formated_amount = tools.misc.format_decimalized_amount(self_with_company.sale_invoiced_amount, currency)

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
