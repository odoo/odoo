from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        if self.env.user._is_internal():
            company_ids = self.env.user.company_ids

            for company in company_ids:
                result["user_companies"]["allowed_companies"][company.id].update(
                    {
                        "timesheet_uom_id": company.timesheet_encode_uom_id.id,
                        "timesheet_uom_factor": company.project_time_mode_id._get_quantity_in_unit(
                            1.0,
                            company.timesheet_encode_uom_id,
                            round=False,
                            raise_if_failure=False,
                        ),
                    }
                )
            result["uom_ids"] = self.get_timesheet_uoms()
            _debug.pipeline(
                "session_timesheet_uoms",
                user=self.env.user,
                companies=company_ids,
                uoms=len(result["uom_ids"]),
            )
        return result

    @api.model
    def get_timesheet_uoms(self):
        company_ids = self.env.user.company_ids
        uom_ids = company_ids.mapped("timesheet_encode_uom_id") | company_ids.mapped(
            "project_time_mode_id"
        )
        return {
            uom.id: {
                "id": uom.id,
                "name": uom.name,
                "rounding": uom.rounding,
                "timesheet_widget": uom.timesheet_widget,
            }
            for uom in uom_ids
        }
