/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { TimesheetOvertimeIndication } from "@timesheet_grid/components/timesheet_overtime_indication/timesheet_overtime_indication";

patch(
    TimesheetOvertimeIndication.prototype,
    {
        get title() {
            if (this.props.name === "project_id") {
                return _t(
                    "Difference between the number of %s ordered on the sales order item and the number of %s delivered",
                    this.props.allocated_hours,
                    this.props.worked_hours
                );
            }
            return super.title;
        },
    }
);
