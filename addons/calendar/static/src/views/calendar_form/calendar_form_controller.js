import { FormController } from "@web/views/form/form_controller";
import { useAskRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

export class CalendarFormController extends FormController {
    setup() {
        super.setup();
        const ormService = useService("orm");
        this.actionService = useService("action");
        this.askRecurrenceUpdatePolicy = useAskRecurrenceUpdatePolicy();

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
        const record = this.model.root;
        const rootValues = record._values;
        let recurrenceUpdate = false;
        if (record.data.recurrency) {
            recurrenceUpdate = await this.askRecurrenceUpdatePolicy();
        }
        if (rootValues.attendees_count == 1 && rootValues.user_id[0] !== rootValues.partner_ids._currentIds[0]) {
            await this._archiveRecord(record.resId, recurrenceUpdate);
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

    /**
     * Archives a calendar event record.
     *
     * @param {number} id - The ID of the record to archive.
     * @param {boolean} recurrenceUpdate - Indicates how the archive of a recurring event will be updated.
     */
    async _archiveRecord(id, recurrenceUpdate) {
        await this.orm.call(this.model.root.resModel, "action_mass_archive", [
            [id], recurrenceUpdate
        ]);
        this.env.config.historyBack();
    }
}
