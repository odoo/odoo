import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { GraphController } from "@web/views/graph/graph_controller";
import { HrActionHelper } from "@hr/views/hr_action_helper";

export class HrGraphController extends GraphController {
    static template = "hr.GraphView";
    static components = { ...GraphController.components, HrActionHelper };
}
export const HrGraphView = {
    ...graphView,
    Controller: HrGraphController,
};

registry.category("views").add("hr_graph_view", HrGraphView);
