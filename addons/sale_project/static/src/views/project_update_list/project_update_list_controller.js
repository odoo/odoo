import { patch } from "@web/core/utils/patch";
import { ProjectUpdateListController } from "@project/views/project_update_list/project_update_list_controller";
import { projectUpdateControllerStatePersistancePatch } from "@sale_project/views/hooks";

patch(ProjectUpdateListController.prototype, projectUpdateControllerStatePersistancePatch());
