import { TaskGanttController } from "@project_enterprise/views/task_gantt/task_gantt_controller";

export class FsmTaskGanttController extends TaskGanttController {
    create(context) {
        if (this.env.isSmall) {
            this.actionService.doAction("industry_fsm.project_task_fsm_mobile_server_action");
            return;
        }
        super.create(context);
    }
}
