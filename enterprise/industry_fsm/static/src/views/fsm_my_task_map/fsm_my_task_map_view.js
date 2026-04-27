import { registry } from "@web/core/registry";
import { projectTaskMapView } from "@project_enterprise/views/project_task_map/project_task_map_view";
import { FsmMyTaskMapController } from "./fsm_my_task_map_controller";

export const fsmMyTaskMapView = {
    ...projectTaskMapView,
    Controller: FsmMyTaskMapController,
};

registry.category("views").add("fsm_my_task_map", fsmMyTaskMapView);
