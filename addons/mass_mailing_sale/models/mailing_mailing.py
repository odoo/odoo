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
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id')

    def _compute_currency_id(self):
        self.currency_id = self.env.company.currency_id

    @api.depends('mailing_domain')
    def _compute_sale_quotation_count(self):
        quotation_data = self.env['sale.order'].sudo()._read_group(
            [('source_id', 'in', self.source_id.ids), ('order_line', '!=', False), ('state', '!=', 'cancel')],
            ['source_id'], ['__count'],
        )
        mapped_data = {source.id: count for source, count in quotation_data}
        for mass_mailing in self:
            mass_mailing.sale_quotation_count = mapped_data.get(mass_mailing.source_id.id, 0)

    @api.depends('mailing_domain')
    def _compute_sale_invoiced_amount(self):
        if self.source_id.ids:
            query_res = self.env.execute_query(SQL(
                """SELECT mailing_id, SUM(amount_total_signed_converted) amount_total_signed_converted_sum
                     FROM (
                         /* Avoid computing amount_total_signed_converted in the subquery as a lot of records are not used. */
                         SELECT mailing_id, amount_total_signed * COALESCE(rate, 1) amount_total_signed_converted
                           FROM (
                               SELECT *,
                                      /* Must use the effective exchange rate when the invoice was created. */
                                      ROW_NUMBER() OVER (PARTITION BY move_id ORDER BY dates_difference) rn
                                 FROM (
                                     SELECT move.id move_id,
                                            move.amount_total_signed,
                                            mailing_mailing.id mailing_id,
                                            currency_rate.rate,
                                            move.date - currency_rate.name dates_difference
                                       FROM account_move move
                                       LEFT JOIN mailing_mailing
                                         ON mailing_mailing.source_id = move.source_id
                                       LEFT JOIN (
                                           SELECT company_id, name, rate
                                             FROM res_currency_rate
                                            WHERE currency_id = %(currency_id)s
                                       ) currency_rate
                                         ON move.company_id = currency_rate.company_id
                                        AND move.date > currency_rate.name
                                      WHERE move.state not in ('draft', 'cancel')
                                        AND move.source_id IN %(source_ids)s
                                 )
                           )
                           WHERE rn = 1
                     )
                    GROUP BY mailing_id""",
                currency_id=self.env.company.currency_id.id,
                source_ids=tuple(self.source_id.ids),
            ))
            data_map = dict(query_res)
        else:
            data_map = {}

        for mailing in self:
            mailing.sale_invoiced_amount = data_map.get(mailing.id, 0.0)

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
            'domain': [('source_id', '=', self.source_id.id)],
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
