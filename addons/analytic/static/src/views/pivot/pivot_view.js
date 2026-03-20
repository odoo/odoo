import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { AnalyticSearchModel } from "@analytic/views/analytic_search_model";
import { AnalyticPivotRenderer } from "@analytic/views/pivot/pivot_renderer";

export const analyticPivotView = {
    ...pivotView,
    Renderer: AnalyticPivotRenderer,
    SearchModel: AnalyticSearchModel,
};

registry.category("views").add("analytic_pivot", analyticPivotView);
