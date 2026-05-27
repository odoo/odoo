import { CrmControlPanel } from "@crm/views/crm_control_panel/crm_control_panel";
import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { ForecastSearchModel } from "@crm/views/forecast_search_model";

export const forecastPivotView = {
    ...pivotView,
    ControlPanel: CrmControlPanel,
    SearchModel: ForecastSearchModel,
};

registry.category("views").add("forecast_pivot", forecastPivotView);
