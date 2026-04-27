/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { PlanningSearchModel } from "../planning_search_model";
import { PlanningRelationalModel } from "../planning_relational_model";


registry.category("views").add("planning_kanban", {
    ...kanbanView,
    SearchModel: PlanningSearchModel,
    Model: PlanningRelationalModel,
});
