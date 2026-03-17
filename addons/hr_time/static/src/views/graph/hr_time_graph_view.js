/** @odoo-module **/

import { graphView } from "@web/views/graph/graph_view";
import { registry } from "@web/core/registry";
import { HrHolidaysGraphModel } from "./hr_time_graph_model";
import { HrHolidaysGraphRenderer } from "./hr_time_graph_renderer";

registry.category("views").add("hr_time_graph", {
    ...graphView,
    Model: HrHolidaysGraphModel,
    Renderer: HrHolidaysGraphRenderer,
    buttonTemplate: "hr_time.HrTimeGraphView.Buttons",
});
