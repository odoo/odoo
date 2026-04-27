/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { TimesheetOvertimeIndication } from "@timesheet_grid/components/timesheet_overtime_indication/timesheet_overtime_indication";

patch(
    TimesheetOvertimeIndication.prototype,
    {
        get title() {
            if (this.props.name === "so_line") {
                return _t("Difference between the allocated %(uom)s (%(allocated_hours)s) on the sales order line and the %(uom)s spent (%(worked_hours)s) on all related projects and tasks", {
                    uom: this.props.uom,
                    allocated_hours: this.props.allocated_hours,
                    worked_hours: this.props.worked_hours,
                });
            }
            return super.title;
        },
    }
);
