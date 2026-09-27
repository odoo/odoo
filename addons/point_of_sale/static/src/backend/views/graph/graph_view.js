import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { PosSearchModel } from "@point_of_sale/backend/views/pos_search_model";

export const posGraphView = {
    ...graphView,
    SearchModel: PosSearchModel,
};

registry.category("views").add("pos_graph_view", posGraphView);
