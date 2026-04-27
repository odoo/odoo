from odoo import models, _


class TrialBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.trial.balance.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code != 'CO':
            return

        # Handles the export of a custom report (XLSX export for l10n_co with a grouping per account, and per partner)
        options.setdefault('buttons', []).append({
            'name': _('XLSX (By Partner)'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'export_to_xlsx_groupby_partner_id',
            'file_export_type': 'xlsx',
        })

        options['l10n_co_reports_groupby_partner_id'] = (previous_options or {}).get('l10n_co_reports_groupby_partner_id')
        if not options['l10n_co_reports_groupby_partner_id']:
            return

        options['columns'].insert(0, {
            'name': _('Partner Name'),
            'column_group_key': options['columns'][-1]['column_group_key'],  # Have to put a column group key so copy the one from the last column
            'expression_label': 'partner_name',
            'sortable': False,
            'figure_type': 'string',
            'blank_if_zero': True,
            'style': 'text-align: center; white-space: nowrap;'
        })
        options['columns'].insert(0, {
            'name': _('Partner VAT'),
            'column_group_key': options['columns'][-1]['column_group_key'],
            'expression_label': 'partner_vat',
            'sortable': False,
            'figure_type': 'string',
            'blank_if_zero': True,
            'style': 'text-align: center; white-space: nowrap;'
        })
        options['column_headers'][0].insert(0, {'name': _('Partners information')})

    def export_to_xlsx_groupby_partner_id(self, options, response=None):
        report = self.env['account.report'].browse(options['report_id'])
        options.update({
            'l10n_co_reports_groupby_partner_id': True,
            'hierarchy': True,
            'unfold_all': True,
        })
        xlsx = report.export_to_xlsx(options, response=response)
        return xlsx
