import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { AnalyticSearchModel } from "@analytic/views/analytic_search_model";

export const analyticListView = {
    ...listView,
    SearchModel: AnalyticSearchModel,
};

registry.category("views").add("analytic_list", analyticListView);
