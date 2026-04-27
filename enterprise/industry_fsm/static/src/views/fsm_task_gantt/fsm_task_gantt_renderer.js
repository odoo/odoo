import { TaskGanttRenderer } from "@project_enterprise/views/task_gantt/task_gantt_renderer";

export class FsmTaskGanttRenderer extends TaskGanttRenderer {
    getSelectCreateDialogProps(params) {
        const props = super.getSelectCreateDialogProps(params);
        if (this.env.isSmall) {
            props.onCreateEdit = () => {
                this.actionService.doAction("industry_fsm.project_task_fsm_mobile_server_action");
            };
        }
        return props;
    }

    getPopoverProps(pill) {
        const props = super.getPopoverProps(pill);
        if (this.env.isSmall) {
            props.buttons.find((obj) => obj.id === "open_view_edit_dialog").onClick = () => {
                const resId = pill.record.id;
                const resModel = this.model.metaData.resModel;
                this.actionService.doAction("industry_fsm.project_task_fsm_mobile_server_action", {
                    additionalContext: {
                        active_id: resId,
                        active_model: resModel,
                    },
                    props: {
                        resModel,
                        resId,
                    },
                });
            };
        }
        return props;
    }
}
