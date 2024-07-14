/** @odoo-module **/

import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { PlanningSearchModel } from "../planning_search_model";


registry.category("views").add("planning_pivot", {
    ...pivotView,
    SearchModel: PlanningSearchModel,
});
