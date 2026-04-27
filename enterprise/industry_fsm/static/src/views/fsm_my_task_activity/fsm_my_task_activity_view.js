import { activityView } from "@mail/views/web/activity/activity_view";
import { registry } from "@web/core/registry";

import { FsmMyTaskActivityController } from "./fsm_my_task_activity_controller";

export const fsmMyTaskActivityView = {
    ...activityView,
    Controller: FsmMyTaskActivityController,
};

registry.category("views").add("fsm_my_task_activity", fsmMyTaskActivityView);
