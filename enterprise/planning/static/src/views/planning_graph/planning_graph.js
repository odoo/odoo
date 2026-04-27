/** @odoo-module **/

import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { PlanningSearchModel } from "../planning_search_model";
import { PlanningGraphModel } from "./planning_graph_model";


registry.category("views").add("planning_graph", {
    ...graphView,
    SearchModel: PlanningSearchModel,
    Model: PlanningGraphModel,
});
