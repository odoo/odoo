import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { GraphController } from "@web/views/graph/graph_controller";

export class HrEmployeeGraphController extends GraphController {
    static template = "hr.EmployeeGraphController";
}

export const hrEmployeeGraphView = {
    ...graphView,
    Controller: HrEmployeeGraphController,
};

registry.category("views").add("hr_employee_graph", hrEmployeeGraphView);
