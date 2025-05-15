from odoo import Command, _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(model="account.journal")
    def _get_payment_bundle_account_journal(self, template_code):
        return {
            "payment_bundle_journal": {
                "name": _("Multiple payments"),
                "type": "cash",
                "outbound_payment_method_line_ids": [
                    Command.create(
                        {
                            "payment_method_id": self.env.ref(
                                "account_payment_bundle.account_payment_out_payment_bundle"
                            ).id,
                            "payment_account_id": "base_outstanding_payments",
                        }
                    ),
                ],
                "inbound_payment_method_line_ids": [
                    Command.create(
                        {
                            "payment_method_id": self.env.ref(
                                "account_payment_bundle.account_payment_in_payment_bundle"
                            ).id,
                            "payment_account_id": "base_outstanding_receipts",
                        }
                    ),
                ],
            },
        }
