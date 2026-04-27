import { ProjectTaskListController } from "@project/views/project_task_list/project_task_list_controller";

export class FsmMyTaskListController extends ProjectTaskListController {
    async openRecord(record) {
        if (!this.env.isSmall) {
            super.openRecord(record);
            return;
        }
        await record.save();
        const resIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.actionService.doAction("industry_fsm.project_task_fsm_mobile_server_action", {
            additionalContext: {
                active_id: record.resId,
                active_model: record.resModel,
            },
            props: {
                resIds,
                resModel: record.resModel,
                resId: record.resId,
            },
            onClose: async () => {
                await record.model.root.load();
            },
        });
    }

    async createRecord({ group } = {}) {
        const list = (group && group.list) || this.model.root;
        if (this.env.isSmall && !(this.editable && !list.isGrouped)) {
            const resIds = list.records.map((datapoint) => datapoint.resId);
            this.actionService.doAction("industry_fsm.project_task_fsm_mobile_server_action", {
                props: {
                    resIds,
                    resModel: list.resModel,
                },
            });
        } else {
            super.createRecord(...arguments);
        }
    }
}
