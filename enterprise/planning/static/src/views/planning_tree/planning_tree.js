/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { PlanningSearchModel } from "../planning_search_model";
import { PlanningRelationalModel } from "../planning_relational_model";


registry.category("views").add("planning_tree", {
    ...listView,
    SearchModel: PlanningSearchModel,
    Model: PlanningRelationalModel,
});
