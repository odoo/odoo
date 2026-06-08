import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { ForecastSearchModel } from "@crm/views/forecast_search_model";

export const forecastGraphView = {
    ...graphView,
    SearchModel: ForecastSearchModel,
};

registry.category("views").add("forecast_graph", forecastGraphView);
