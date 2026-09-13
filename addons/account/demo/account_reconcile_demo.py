import time

from odoo import Command, _, api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    @_debug.perf.timed
    def _account_reconcile_install_demo(self, companies):
        if not isinstance(companies, models.BaseModel):
            companies = self.env["res.company"].browse(companies)
        _debug.pipeline("reconcile_demo_started", company=companies)
        for company in companies:
            _debug.pipeline("reconcile_demo_loading", company=company)
            self.with_company(company).sudo()._load_data(
                {
                    "account.move": {
                        "demo_invoice_deferred": {
                            "move_type": "out_invoice",
                            "partner_id": "base.res_partner_1",
                            "invoice_user_id": "base.user_demo",
                            "invoice_date": time.strftime("%Y-01-01"),
                            "invoice_line_ids": [
                                Command.create(
                                    {
                                        "name": _("Subscription 12 months"),
                                        "quantity": 1,
                                        "price_unit": 120,
                                        "deferred_start_date": time.strftime(
                                            "%Y-01-01"
                                        ),
                                        "deferred_end_date": time.strftime("%Y-12-31"),
                                    }
                                ),
                            ],
                        },
                        "demo_bill_deferred": {
                            "move_type": "in_invoice",
                            "partner_id": "base.res_partner_1",
                            "invoice_user_id": "base.user_demo",
                            "invoice_date": time.strftime("%Y-01-01"),
                            "invoice_line_ids": [
                                Command.create(
                                    {
                                        "name": _("Insurance 12 months"),
                                        "quantity": 1,
                                        "price_unit": 1200,
                                        "deferred_start_date": time.strftime(
                                            "%Y-01-01"
                                        ),
                                        "deferred_end_date": time.strftime("%Y-12-31"),
                                    }
                                ),
                            ],
                        },
                    },
                }
            )
