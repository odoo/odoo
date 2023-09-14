/** @odoo-module **/

import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { ForecastTemporalFillSearchModel } from "@crm/views/forecast_temporal_fill_search_model";

export const forecastGraphView = {
    ...graphView,
    SearchModel: ForecastTemporalFillSearchModel,
};

registry.category("views").add("forecast_graph", forecastGraphView);
