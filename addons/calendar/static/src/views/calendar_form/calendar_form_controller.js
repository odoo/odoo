/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

export class CalendarFormController extends FormController {
    setup() {
        super.setup();
        const ormService = useService("orm");
        this.actionService = useService("action");

        onWillStart(async () => {
            this.discussVideocallLocation = await ormService.call(
                "calendar.event",
                "get_discuss_videocall_location"
            );
        });
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        const action = clickParams.name;
        if (action === "clear_videocall_location" || action === "set_discuss_videocall_location") {
            let newVal = "";
            let videoCallSource = "custom";
            let changes = {};
            if (action === "set_discuss_videocall_location") {
                newVal = this.discussVideocallLocation;
                videoCallSource = "discuss";
                changes.access_token = this.discussVideocallLocation.split("/").pop();
            }
            changes = Object.assign(changes, {
                videocall_location: newVal,
                videocall_source: videoCallSource,
            });
            this.model.root.update(changes);
            return false; // no continue
        }
        return super.beforeExecuteActionButton(...arguments);
    }

    async deleteRecord() {
        const action = await this.orm.call("calendar.event", "action_unlink_event", [
            this.model.root.resId,
            this.model.root.data.partner_ids.resIds,
            this.model.root.data.recurrence_update,
        ]);
        this.actionService.doAction(action);
    }
}
