from datetime import datetime

from dateutil import relativedelta

from odoo import fields, models


class PayslipLinesContributionRegister(models.TransientModel):
    _name = "payslip.lines.contribution.register"
    _description = "Payslip Lines by Contribution Registers"

    date_from = fields.Date(required=True, default=datetime.now().strftime("%Y-%m-01"))
    date_to = fields.Date(
        required=True,
        default=str(
            datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1)
        )[:10],
    )

    def print_report(self):
        active_ids = self.env.context.get("active_ids", [])
        datas = {
            "ids": active_ids,
            "model": "hr.contribution.register",
            "form": self.read()[0],
        }
        return self.env.ref("payroll.action_contribution_register").report_action(
            [], data=datas
        )
