import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { AccountAnalyticSearchModel } from "@account/js/search/search_model/search_model";

const accountGraphView = {
    ...graphView,
    SearchModel: AccountAnalyticSearchModel,
};

registry.category("views").add("account_analytic_graph", accountGraphView);
