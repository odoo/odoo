import { projectEnterpriseTaskListView } from "@project_enterprise/views/project_task_tree/project_task_list_view";
import { registry } from "@web/core/registry";
import { FsmMyTaskListController } from "./fsm_my_task_list_controller";

export const fsmMyTaskListView = {
    ...projectEnterpriseTaskListView,
    Controller: FsmMyTaskListController,
};

registry.category("views").add("fsm_my_task_list", fsmMyTaskListView);
