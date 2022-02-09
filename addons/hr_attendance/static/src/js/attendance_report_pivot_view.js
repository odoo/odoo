/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PivotView } from "@web/views/pivot/pivot_view";

const viewRegistry = registry.category("views");

export class AttendanceReportPivotView extends PivotView {
    /**
     * @override
     */
    onOpenView(cell) {
        if (cell.value === undefined || this.model.metaData.disableLinking) {
            return;
        }

        const context = Object.assign({}, this.model.searchParams.context);
        Object.keys(context).forEach((x) => {
            if (x === "group_by" || x.startsWith("search_default_")) {
                delete context[x];
            }
        });

        const group = {
            rowValues: cell.groupId[0],
            colValues: cell.groupId[1],
            originIndex: cell.originIndexes[0],
        };
        const domain = this.model.getGroupDomain(group);

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this.model.metaData.title,
            res_model: 'hr.attendance',
            views: [[false, "list"], [false, "form"]],
            view_mode: "list",
            target: "current",
            context,
            domain,
        });
    }
}

viewRegistry.add("attendance_report_pivot", AttendanceReportPivotView);
