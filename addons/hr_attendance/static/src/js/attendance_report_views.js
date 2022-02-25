/** @odoo-module **/

import { registry } from "@web/core/registry";
import { GraphView } from "@web/views/graph/graph_view";
import { PivotView } from "@web/views/pivot/pivot_view";

const viewRegistry = registry.category("views");

/**
 * Open the hr.attendance instead of the report list view.
 */
function openView(component, domain, views, context) {
    component.actionService.doAction({
        type: "ir.actions.act_window",
        name: component.model.metaData.title,
        res_model: 'hr.attendance',
        views: [[false, "list"], [false, "form"]],
        view_mode: "list",
        target: "current",
        context,
        domain,
    });
}

export class AttendanceReportGraphView extends GraphView {
    /**
     * @override
     */
    openView(domain, views, context) {
        openView(this, domain, views, context);
    }
}

viewRegistry.add("attendance_report_graph", AttendanceReportGraphView);

export class AttendanceReportPivotView extends PivotView {
    /**
     * @override
     */
    openView(domain, views, context) {
        openView(this, domain, views, context);
    }
}

viewRegistry.add("attendance_report_pivot", AttendanceReportPivotView);
