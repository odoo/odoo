import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { ForecastSearchModel } from "@crm/views/forecast_search_model";

export const forecastPivotView = {
    ...pivotView,
    SearchModel: ForecastSearchModel,
};

registry.category("views").add("forecast_pivot", forecastPivotView);
