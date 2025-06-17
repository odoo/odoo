import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

import { graphView } from "@web/views/graph/graph_view";
import { GraphController } from "@web/views/graph/graph_controller";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { useService } from "@web/core/utils/hooks";
import { patchHrEmployee } from "./patch_hr_employee";

export class HrGraphController extends GraphController {
    static template = "hr.GraphView";
}
patchHrEmployee(HrGraphController);

export class HrGraphRenderer extends GraphRenderer {
    static template = "hr.GraphRenderer";

    setup() {
        super.setup();
        this.actionHelperService = useService("hr_action_helper");
        onWillStart(async () => {
            this.showActionHelper = await this.actionHelperService.showActionHelper();
        });
    }
}

export const HrGraphView = {
    ...graphView,
    Controller: HrGraphController,
    Renderer: HrGraphRenderer,
};

registry.category("views").add("hr_graph_view", HrGraphView);
