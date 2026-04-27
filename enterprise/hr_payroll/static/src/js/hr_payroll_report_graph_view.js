
import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { useOpenViews } from "./hooks";

export class HrPayrollReportGraphRenderer extends graphView.Renderer {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.openView = useOpenViews();
    }
}

registry.category("views").add("hr_payroll_report_graph", {
    ...graphView,
    Renderer: HrPayrollReportGraphRenderer,
});
