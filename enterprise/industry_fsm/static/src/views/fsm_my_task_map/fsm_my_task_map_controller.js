import { MapController } from "@web_map/map_view/map_controller";

export class FsmMyTaskMapController extends MapController {
    openRecords(ids) {
        if (ids.length === 1 && this.env.isSmall) {
            const resIds = this.model.data.records.map((data) => data.id);
            return this.action.doAction("industry_fsm.project_task_fsm_mobile_server_action", {
                additionalContext: {
                    active_id: ids[0],
                    active_model: this.props.resModel,
                },
                props: {
                    resIds,
                    resModel: this.props.resModel,
                    resId: ids[0],
                },
            });
        }
        super.openRecords(ids);
    }
}
