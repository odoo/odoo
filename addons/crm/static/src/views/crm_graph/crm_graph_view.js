import { CrmSearchModel } from "@crm/views/crm_search_model";
import { graphView } from "@web/views/graph/graph_view";
import { registry } from "@web/core/registry";

export const crmGraphView = {
    ...graphView,
    SearchModel: CrmSearchModel,
}

registry.category("views").add("crm_graph", crmGraphView);
