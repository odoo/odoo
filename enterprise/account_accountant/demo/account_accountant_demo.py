import time

from odoo import api, models, Command, _


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _account_accountant_install_demo(self, companies):
        if not isinstance(companies, models.BaseModel):
            companies = self.env['res.company'].browse(companies)
        for company in companies:
            self.with_company(company).sudo()._load_data({
                'account.move': {
                    'demo_invoice_deferred': {
                        'move_type': 'out_invoice',
                        'partner_id': 'base.res_partner_1',
                        'invoice_user_id': 'base.user_demo',
                        'invoice_date': time.strftime('%Y-01-01'),
                        'invoice_line_ids': [
                            Command.clear(),
                            Command.create({
                                'name': _('Subscription 12 months'),
                                'quantity': 1,
                                'price_unit': 120,
                                'deferred_start_date': time.strftime('%Y-01-01'),
                                'deferred_end_date': time.strftime('%Y-12-31'),
                            }),
                        ]
                    },
                    'demo_bill_deferred': {
                        'move_type': 'in_invoice',
                        'partner_id': 'base.res_partner_1',
                        'invoice_user_id': 'base.user_demo',
                        'invoice_date': time.strftime('%Y-01-01'),
                        'invoice_line_ids': [
                            Command.clear(),
                            Command.create({
                                'name': _('Insurance 12 months'),
                                'quantity': 1,
                                'price_unit': 1200,
                                'deferred_start_date': time.strftime('%Y-01-01'),
                                'deferred_end_date': time.strftime('%Y-12-31'),
                            }),
                        ]
                    },
                },
            })
