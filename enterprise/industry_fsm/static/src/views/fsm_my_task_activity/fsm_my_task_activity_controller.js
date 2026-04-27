import { ActivityController } from "@mail/views/web/activity/activity_controller";

export class FsmMyTaskActivityController extends ActivityController {
    openRecord(record, mode) {
        if (this.env.isSmall) {
            const resIds = this.model.root.records.map((datapoint) => datapoint.resId);
            return this.action.doAction("industry_fsm.project_task_fsm_mobile_server_action", {
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
        return super.openRecord(record, mode);
    }
}
