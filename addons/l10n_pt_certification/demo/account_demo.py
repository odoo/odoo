import logging

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_demo_data(self, company=False):
        if company and company.account_fiscal_country_id.code == 'PT':
            self._create_l10n_at_series_demo(company)
            invoices = (
                    self.with_company(company).ref('demo_invoice_1')
                    + self.with_company(company).ref('demo_invoice_2')
                    + self.with_company(company).ref('demo_invoice_3')
                    + self.with_company(company).ref('demo_invoice_followup')
                    + self.with_company(company).ref('demo_invoice_5')
                    + self.with_company(company).ref('demo_invoice_equipment_purchase')
                    + self.with_company(company).ref('demo_move_auto_reconcile_1')
                    + self.with_company(company).ref('demo_move_auto_reconcile_2')
                    + self.with_company(company).ref('demo_move_auto_reconcile_3')
                    + self.with_company(company).ref('demo_move_auto_reconcile_4')
                    + self.with_company(company).ref('demo_move_auto_reconcile_5')
                    + self.with_company(company).ref('demo_move_auto_reconcile_6')
                    + self.with_company(company).ref('demo_move_auto_reconcile_7')
                    + self.with_company(company).ref('demo_move_auto_reconcile_8')
                    + self.with_company(company).ref('demo_move_auto_reconcile_9')
            )
            # we need to ensure AT Series created after the moves are added to the demo moves
            invoices._compute_l10n_pt_at_series_id()
            for move in invoices:
                try:
                    move.action_post()
                except (UserError, ValidationError):
                    _logger.exception('Error while posting demo data')
        return super()._post_load_demo_data(company)

    def _create_l10n_at_series_demo(self, company):
        if company and company.country_code == "PT":
            # Create demo AT series. Demo data contains moves from the current and previous month,
            # which can occasionally fall in the year prior
            if fields.Date.context_today(self).month == 1:
                years = (fields.Date.context_today(self).year, fields.Date.context_today(self).year - 1)
            else:
                years = (fields.Date.context_today(self).year,)
            sale_journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'sale'),
            ], limit=1)
            bank_journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'bank'),
            ], limit=1)
            for year in years:
                self.env['l10n_pt.at.series'].create([{
                    'name': str(year),
                    'company_id': company.id,
                    'training_series': True,
                    'sale_journal_id': sale_journal.id,
                    'payment_journal_id': bank_journal.id,
                    'at_series_line_ids': [
                        Command.create({
                            'type': series_type,
                            'prefix': prefix,
                            'at_code': f'AT-{prefix}{year}',
                        })
                        for series_type, prefix in (('out_invoice', 'INV'), ('out_refund', 'RINV'), ('payment_receipt', 'RG'))
                    ]
                }])
