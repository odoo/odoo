import { FormController } from "@web/views/form/form_controller";
import { useAskRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import { useUnlinkCalendarEvent } from "@calendar/views/hooks";
import { useService } from "@web/core/utils/hooks";

export class CalendarFormController extends FormController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.askRecurrenceUpdatePolicy = useAskRecurrenceUpdatePolicy();
        this.unlinkCalendarEvent = useUnlinkCalendarEvent();
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        const action = clickParams.name;
        if (action === "clear_videocall_location") {
            this.model.root.clearLocation();
            return false;
        } else if (action === "set_discuss_videocall_location") {
            this.model.root.setLocation();
            return false;
        }
        return super.beforeExecuteActionButton(...arguments);
    }

    /**
     * @override
     */
    async deleteRecord() {
        const record = this.model.root;
        const rootValues = record._values;
        if (rootValues.attendees_count == 1 && rootValues.user_id.id !== rootValues.partner_ids._currentIds[0]) {
            await this._archiveRecord(record);
        } else {
            await this.unlinkCalendarEvent({
                resId: record.resId,
                partnerIds: record.data.partner_ids.resIds,
                recurrency: record.data.recurrency,
                start: record.data.start,
                defaultAction: () => this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps),
                nextAction: { type: "ir.actions.act_url", target: "self", url: "/odoo/calendar" },
            });
        }
    }

    /**
     * Archives a calendar event record.
     */
    async _archiveRecord(record) {
        let recurrenceUpdate = false;
        if (record.data.recurrency) {
            recurrenceUpdate = await this.askRecurrenceUpdatePolicy();
        }
        await this.orm.call(this.model.root.resModel, "action_mass_archive", [
            [record.resId], recurrenceUpdate
        ]);
        this.env.config.historyBack();
    }
}
