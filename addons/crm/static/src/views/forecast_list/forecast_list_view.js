/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ForecastTemporalFillSearchModel } from "@crm/views/forecast_temporal_fill_search_model";

export const forecastListView = {
    ...listView,
    SearchModel: ForecastTemporalFillSearchModel,
};

registry.category("views").add("forecast_list", forecastListView);
