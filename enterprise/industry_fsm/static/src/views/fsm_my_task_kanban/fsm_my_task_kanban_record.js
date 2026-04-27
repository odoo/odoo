import { ProjectTaskKanbanRecord } from "@project/views/project_task_kanban/project_task_kanban_record";
import { CANCEL_GLOBAL_CLICK } from "@web/views/kanban/kanban_record";

export class FsmMyTaskKanbanRecord extends ProjectTaskKanbanRecord {
    onGlobalClick(ev) {
        if (!this.env.isSmall) {
            super.onGlobalClick(ev);
            return;
        }
        if (!ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            const { record } = this.props;
            const resIds = record.model.root.records.map((datapoint) => datapoint.resId);
            this.action.doAction("industry_fsm.project_task_fsm_mobile_server_action", {
                additionalContext: {
                    active_id: record.resId,
                    active_model: record.resModel,
                },
                props: {
                    resIds,
                    resModel: record.resModel,
                    resId: record.resId,
                },
            });
        }
    }
}
