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

    /**
     * Custom delete function for calendar events, which can call the unlink action or not.
     * When there is only one attendee, who is also the organizer, and the organizer is not listed in the current attendees, it performs the default delete.
     * Otherwise, it calls the unlink action on the server.
     */
    async deleteRecord() {
        const rootValues = this.model.root._values;
        if (rootValues.attendees_count == 1 && rootValues.user_id[0] !== rootValues.partner_ids._currentIds[0]) {
            // Call the default delete if the event has only one attendee and the user is not listed in partner_ids.
            super.deleteRecord(...arguments);
        } else {
            await this.orm.call("calendar.event", "action_unlink_event", [
                this.model.root.resId,
                this.model.root.data.partner_ids.resIds,
                this.model.root.data.recurrence_update,
            ])
            .then((action) => {
                if (action && action.context) {
                    this.actionService.doAction(action);
                } else {
                    this.actionService.doAction({
                        type: "ir.actions.act_window",
                        name: "Meetings",
                        res_model: "calendar.event",
                        view_mode: "calendar",
                        views: [[false, "calendar"]],
                        target: "current",
                    });
                }
            });
        }
    }
}
