from odoo import api, models
from odoo.fields import Domain


class ReportPos_HrSingle_Employee_Sales_Report(models.AbstractModel):
    _name = "report.pos_hr.single_employee_sales_report"
    _inherit = ["report.point_of_sale.report_saledetails"]
    _description = "Session sales details for a single employee"

    def _get_domain_orders(
        self,
        date_start=False,
        date_stop=False,
        config_ids=False,
        session_ids=False,
        *,
        employee_id=False,
        **kwargs,
    ):
        domain = super()._get_domain_orders(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )

        if employee_id:
            domain &= Domain("employee_id", "=", employee_id)

        return domain

    def _prepare_get_sale_details_args_kwargs(self, data):
        args, kwargs = super()._prepare_get_sale_details_args_kwargs(data)
        kwargs["employee_id"] = data.get("employee_id")
        return args, kwargs

    @api.model
    def get_sale_details(
        self,
        date_start=False,
        date_stop=False,
        config_ids=False,
        session_ids=False,
        *,
        employee_id=False,
        **kwargs,
    ):
        data = super().get_sale_details(
            date_start,
            date_stop,
            config_ids,
            session_ids,
            employee_id=employee_id,
            **kwargs,
        )

        if employee_id:
            employee = self.env["hr.employee"].browse(employee_id).exists()
            data["employee_name"] = (
                employee.name if employee else self.env._("Unknown Employee")
            )

        return data
