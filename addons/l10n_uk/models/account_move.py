# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        # Display a warning if wrongly used

        reclaimable_tax_ids = set()

        chart_template = self.env['account.chart.template']
        for company in self.company_id:
            template_tax = chart_template.with_company(company).ref('PT_20_FRS', raise_if_not_found=False)
            if template_tax:
                reclaimable_tax_ids.add(template_tax.id)

        checked_moves = self.filtered(
            lambda move: move.move_type in ('in_invoice', 'in_receipt')
            and any(reclaimable_tax_ids.intersection(line.tax_ids.ids) for line in move.invoice_line_ids)
        )
        warning_moves = self.env['account.move']
        gbp_currency_id = self.env.ref('base.GBP')
        for move in checked_moves:
            taxed_lines = move.invoice_line_ids.filtered(
                lambda line: reclaimable_tax_ids.intersection(line.tax_ids.ids)
            )
            has_ineligible_lines = any(
                not line.product_id
                or line.product_id.type != 'consu'
                or gbp_currency_id.compare_amounts(
                    move.currency_id._convert(
                        line.price_total,
                        gbp_currency_id,
                        move.company_id,
                        move.invoice_date or move.date,
                    ),
                    2000,
                ) < 0
                for line in taxed_lines
            )
            if has_ineligible_lines:
                warning_moves |= move

        result = super().action_post()
        if warning_moves:
            # Names are only known once the moves are posted
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Check Flat Rate Scheme VAT reclaim'),
                    'message': _(
                        'Wrong use of FRS reclaimable tax in: %(bills)s. '
                        'Taxed purchase must be a single qualifying goods purchase of at least '
                        '£2,000 (including VAT).',
                        bills=', '.join(warning_moves.mapped('display_name')),
                    ),
                    'type': 'warning',
                    'sticky': True,
                    'next': result or {'type': 'ir.actions.act_window_close'},
                },
            }
        return result
