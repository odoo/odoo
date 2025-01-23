import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { AccountAnalyticSearchModel } from "@account/js/search/search_model/search_model";

const accountPivotView = {
    ...pivotView,
    SearchModel: AccountAnalyticSearchModel,
};

registry.category("views").add("account_analytic_pivot", accountPivotView);
