import { kanbanView } from "@web/views/kanban/kanban_view";
import { RottingKanbanController } from "./rotting_kanban_controller";
import { RottingKanbanModel } from "./rotting_kanban_model";
import { RottingKanbanRenderer } from "./rotting_kanban_renderer";
import { registry } from "@web/core/registry";

export const rottingKanbanView = {
    ...kanbanView,
    Controller: RottingKanbanController,
    Model: RottingKanbanModel,
    Renderer: RottingKanbanRenderer,
};

registry.category("views").add("rotting_kanban", rottingKanbanView);
