from odoo import models, _


class IndianTDSTCSReportCustomHandler(models.AbstractModel):
    _name = 'l10n_in_withholding.tds.tcs.report.handler'
    _inherit = 'account.generic.tax.report.handler'
    _description = 'Indian Tax Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        if warnings is not None:
            AccountMove = self.env['account.move']
            domain = [
                ('date', '>=', options['date']['date_from']),
                ('date', '<=', options['date']['date_to']),
                ('state', '=', 'posted'),
                ('commercial_partner_id.l10n_in_pan', '=', False),
            ]
            if report.id == self.env.ref("l10n_in_withholding.tds_report").id:
                domain += [('invoice_line_ids.tax_ids.l10n_in_tds_tax_type', '=', 'purchase')]
                invalid_move_ids = AccountMove.search(domain).l10n_in_withholding_ref_move_id.ids
            elif report.id == self.env.ref("l10n_in_withholding.tcs_report").id:
                domain += [('invoice_line_ids.tax_ids.l10n_in_section_id.tax_source_type', '=', 'tcs')]
                invalid_move_ids = AccountMove.search(domain).ids
            if invalid_move_ids:
                warnings['l10n_in_reports_tds_tcs.missing_pan_tds_tcs_warning'] = {'ids': invalid_move_ids, 'alert_type': 'warning'}
        return []

    def open_missing_pan_tds_tcs_moves(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries'),
            'res_model': 'account.move',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', params['ids'])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }
