import { patch } from "@web/core/utils/patch";
import { ProjectUpdateKanbanController } from "@project/views/project_update_kanban/project_update_kanban_controller";
import { projectUpdateControllerStatePersistancePatch } from "@sale_project/views/hooks";

patch(ProjectUpdateKanbanController.prototype, projectUpdateControllerStatePersistancePatch());
