# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SocialPost(models.Model):
    _inherit = 'social.post'

    sale_quotation_count = fields.Integer('Quotation Count', groups='sales_team.group_sale_salesman',
                                          compute='_compute_sale_quotation_count', compute_sudo=True)
    sale_invoiced_amount = fields.Integer('Invoiced Amount', groups='sales_team.group_sale_salesman',
                                          compute='_compute_sale_invoiced_amount', compute_sudo=True)

    def _compute_sale_quotation_count(self):
        quotation_data = self.env['sale.order']._read_group(
            [('source_id', 'in', self.source_id.ids)],
            ['source_id'], ['__count'])
        mapped_data = {source.id: count for source, count in quotation_data}
        for post in self:
            post.sale_quotation_count = mapped_data.get(post.source_id.id, 0)


    def _compute_sale_invoiced_amount(self):
        if self.source_id.ids:
            query = """SELECT move.source_id as source_id, -SUM(line.balance) as price_subtotal
                        FROM account_move_line line
                        INNER JOIN account_move move ON line.move_id = move.id
                        WHERE move.state not in ('draft', 'cancel')
                            AND move.source_id IN %s
                            AND move.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
                            AND move.company_id IN %s
                            AND line.account_id IS NOT NULL
                            AND line.display_type = 'product'
                        GROUP BY move.source_id
                        """
            self._cr.execute(query, [tuple(self.source_id.ids), tuple(self.env.companies.ids)])
            query_res = self._cr.dictfetchall()
            mapped_data = {datum['source_id']: datum['price_subtotal'] for datum in query_res}

            for post in self:
                post.sale_invoiced_amount = mapped_data.get(post.source_id.id, 0)
        else:
            for post in self:
                post.sale_invoiced_amount = 0

    def action_redirect_to_quotations(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        action['domain'] = self._get_sale_utm_domain()
        action['context'] = {'create': False}
        return action

    def action_redirect_to_invoiced(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action['context'] = {
            'create': False,
            'edit': False,
            'view_no_maturity': True
        }
        action['domain'] = [
            ('source_id', '=', self.source_id.id),
            ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')),
            ('state', 'not in', ['draft', 'cancel'])
        ]
        return action

    def _get_sale_utm_domain(self):
        """ We want all records that match the UTMs """
        return [('source_id', '=', self.source_id.id)]
