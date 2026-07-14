import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { AnalyticSearchModel } from "@analytic/views/analytic_search_model";

export const analyticGraphView = {
    ...graphView,
    SearchModel: AnalyticSearchModel,
};

registry.category("views").add("analytic_graph", analyticGraphView);
