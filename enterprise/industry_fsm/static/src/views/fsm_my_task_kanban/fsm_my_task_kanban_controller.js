import { KanbanController } from "@web/views/kanban/kanban_controller";

export class FsmMyTaskKanbanController extends KanbanController {
    async createRecord() {
        const { onCreate } = this.props.archInfo;
        const { root } = this.model;
        if (
            this.env.isSmall &&
            (!this.canQuickCreate || (onCreate && onCreate !== "quick_create"))
        ) {
            const resIds = root.records.map((datapoint) => datapoint.resId);
            this.actionService.doAction("industry_fsm.project_task_fsm_mobile_server_action", {
                props: {
                    resIds,
                    resModel: this.props.resModel,
                },
                additionalContext: root.context,
                onClose: async () => {
                    await root.load();
                    this.model.useSampleModel = false;
                    this.render(true);
                },
            });
            return;
        } else {
            super.createRecord();
        }
    }
}
