/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { graphView } from "@web/views/graph/graph_view";
import { pivotView } from "@web/views/pivot/pivot_view";
import { useComponent } from "@odoo/owl";

const viewRegistry = registry.category("views");

/**
 * Open the hr.attendance instead of the report list view.
 */
function useOpenView() {
    const action = useService('action');
    const component = useComponent();

    return (domain, views, context) => {
        action.doAction({
            type: "ir.actions.act_window",
            name: component.model.metaData.title,
            res_model: 'hr.attendance',
            views: [[false, "list"], [false, "form"]],
            view_mode: "list",
            target: "current",
            context,
            domain,
        });
    };
}

export class AttendanceReportGraphRenderer extends graphView.Renderer {
    setup() {
        super.setup();
        this.openView = useOpenView();
    }
}

viewRegistry.add("attendance_report_graph", {
    ...graphView,
    Renderer: AttendanceReportGraphRenderer
});

export class AttendanceReportPivotRenderer extends pivotView.Renderer {
    setup() {
        super.setup();
        this.openView = useOpenView();
    }
}

viewRegistry.add("attendance_report_pivot", {
    ...pivotView,
    Renderer: AttendanceReportPivotRenderer
});
