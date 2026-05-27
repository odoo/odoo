import { CrmControlPanel } from "@crm/views/crm_control_panel/crm_control_panel";
import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { ForecastSearchModel } from "@crm/views/forecast_search_model";

export const forecastGraphView = {
    ...graphView,
    ControlPanel: CrmControlPanel,
    SearchModel: ForecastSearchModel,
};

registry.category("views").add("forecast_graph", forecastGraphView);
