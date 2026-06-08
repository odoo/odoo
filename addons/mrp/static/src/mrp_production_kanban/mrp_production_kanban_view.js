import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { MrpProductionKanbanRenderer } from "./mrp_production_kanban_renderer";

export const mrpProductionKanbanView = {
    ...kanbanView,
    Renderer: MrpProductionKanbanRenderer,
};

registry.category("views").add("mrp_production_kanban", mrpProductionKanbanView);
