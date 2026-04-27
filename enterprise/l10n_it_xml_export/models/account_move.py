from dateutil.relativedelta import relativedelta

from odoo import _, models, osv
from odoo.tools import date_utils
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """This action will be called by the POST button on a tax report account move.
           As posting this move will generate the XML report, it won't call `action_post`
           immediately, but will open the wizard that configures this XML file.
           Validating the wizard will resume the `action_post` and take these options in
           consideration when generating the XML report.
        """
        closing_moves = self.filtered(lambda move: move.tax_closing_report_id)
        # The following process is only required if we are posting an Italian tax closing move.
        if (
            closing_moves
            and "IT" in self.mapped('tax_country_code')
            and "l10n_it_xml_export_monthly_tax_report_options" not in self.env.context
        ):
            closing_max_date = max(closing_moves.mapped('date'))
            last_posted_tax_closing = self.env['account.move'].search(osv.expression.AND([
                self.env['account.move']._check_company_domain(self.company_id),
                [
                    ('tax_closing_report_id', '!=', False),
                    ('move_type', '=', 'entry'),
                    ('state', '=', 'posted'),
                    ('date', '<', closing_max_date)
                ],
                osv.expression.OR([
                    [('fiscal_position_id.country_id.code', '=', 'IT')],
                    [
                        ('fiscal_position_id', '=', False),
                        ('company_id.account_fiscal_country_id.code', '=', 'IT'),
                    ]
                ])
            ]), order='date desc', limit=1)
            quarterly = self.env.company.account_tax_periodicity == 'trimester'
            if last_posted_tax_closing:
                # If there is a posted tax closing, we only check that there is no gap in the months.
                maximum_gap = 3 if quarterly else 1
                if closing_max_date.month - last_posted_tax_closing[0].date.month > maximum_gap:
                    raise UserError(_("You cannot post the tax closing of %(month)s without posting the previous tax closing first.", month=closing_max_date.strftime("%m/%Y")))
            else:
                # If no tax closing has ever been posted, we have to check if there are Italian taxes in a previous month (meaning a missing tax closing).
                previous_move = self.env['account.move'].search_fetch(osv.expression.AND([
                    self.env['account.move']._check_company_domain(self.company_id),
                    [
                        ('tax_closing_report_id', '=', False),
                        ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
                        ('date', '<', date_utils.start_of(closing_max_date, 'quarter' if quarterly else 'month')),
                    ],
                    osv.expression.OR([
                        [('fiscal_position_id.country_id.code', '=', 'IT')],
                        [
                            ('fiscal_position_id', '=', False),
                            ('company_id.account_fiscal_country_id.code', '=', 'IT'),
                        ]
                    ])
                ]), order='date asc', field_names=['date'], limit=1)
                if previous_move:
                    report = self.env.ref('l10n_it.tax_monthly_report_vat')
                    current = previous_move.date.replace(day=1)
                    while current <= closing_max_date.replace(day=1):
                        date_from = date_utils.start_of(current, 'month')
                        date_to = date_utils.end_of(current, 'month')
                        at_date_options = report.get_options({
                            'selected_variant_id': report.id,
                            'date': {
                                'date_from': date_from,
                                'date_to': date_to,
                                'mode': 'range',
                                'filter': 'custom',
                            },
                        })
                        at_date_report_lines = report._get_lines(at_date_options)
                        balance_col_idx = next((idx for idx, col in enumerate(at_date_options.get('columns', [])) if col.get('expression_label') == 'balance'), None)
                        if any(line['columns'][balance_col_idx]['no_format'] for line in at_date_report_lines if line['name'].startswith('VP')):
                            raise UserError(_("You cannot post the tax closing of that month because older months have taxes to report but no tax closing posted. Oldest month is %(month)s", month=current.strftime("%m/%Y")))
                        current += relativedelta(months=1)

            # If the process has not been stopped yet, we open the wizard for the xml export.
            view_id = self.env.ref('l10n_it_xml_export.monthly_tax_report_xml_export_wizard_view').id
            ctx = self.env.context.copy()
            ctx.update({
                'l10n_it_moves_to_post': self.ids,
                'l10n_it_xml_export_monthly_tax_report_options': {
                    'date': {'date_to': closing_max_date},
                },
            })

            return {
                'name': _('Post a tax report entry'),
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'res_model': 'l10n_it_xml_export.monthly.tax.report.xml.export.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': ctx,
            }

        return super().action_post()
