import { kanbanView } from "@web/views/kanban/kanban_view";
import { RottingKanbanArchParser } from "./rotting_kanban_arch_parser";
import { RottingKanbanController } from "./rotting_kanban_controller";
import { RottingKanbanRenderer } from "./rotting_kanban_renderer";
import { registry } from "@web/core/registry";

export const rottingKanbanView = {
    ...kanbanView,
    ArchParser: RottingKanbanArchParser,
    Controller: RottingKanbanController,
    Renderer: RottingKanbanRenderer,
};

registry.category("views").add("rotting_kanban", rottingKanbanView);
