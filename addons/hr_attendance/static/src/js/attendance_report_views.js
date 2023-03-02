/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { graphView } from "@web/views/graph/graph_view";
import { pivotView } from "@web/views/pivot/pivot_view";

const { useComponent } = owl;

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

export class AttendanceReportGraphController extends graphView.Controller {
    setup() {
        super.setup();
        this.openView = useOpenView();
    }
}

viewRegistry.add("attendance_report_graph", {
    ...graphView,
    Controller: AttendanceReportGraphController
});

export class AttendanceReportPivotController extends pivotView.Controller {
    setup() {
        super.setup();
        this.openView = useOpenView();
    }
}

viewRegistry.add("attendance_report_pivot", {
    ...pivotView,
    Controller: AttendanceReportPivotController
});
