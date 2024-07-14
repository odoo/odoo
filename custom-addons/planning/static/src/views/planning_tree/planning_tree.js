/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { PlanningSearchModel } from "../planning_search_model";


registry.category("views").add("planning_tree", {
    ...listView,
    SearchModel: PlanningSearchModel,
});
