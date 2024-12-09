import { FormController } from "@web/views/form/form_controller";
import { useAskRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

export class CalendarFormController extends FormController {
    setup() {
        super.setup();
        const ormService = useService("orm");
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
     * Archives a record, ask for the recurrence update policy in case of recurrent event.
     */
    async deleteRecord() {
        let record = this.model.root;
        let recurrenceUpdate = false;
        if (record.data.recurrency) {
            recurrenceUpdate = await this.askRecurrenceUpdatePolicy();
            if (recurrenceUpdate) {
                await this._archiveRecord(record.resId, recurrenceUpdate);
            }
        } else {
            await super.deleteRecord(...arguments);
        }
    }

    async _archiveRecord(id, recurrenceUpdate) {
        await this.orm.call(this.model.root.resModel, "action_mass_archive", [
            [id], recurrenceUpdate
        ].filter(Boolean));
        this.env.config.historyBack();
    }
}
