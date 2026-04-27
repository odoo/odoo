import { FormController } from "@web/views/form/form_controller";
import { useAskRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import { useUnlinkCalendarEvent } from "@calendar/views/hooks";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class CalendarFormController extends FormController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.askRecurrenceUpdatePolicy = useAskRecurrenceUpdatePolicy();
        this.isPostSaveNotificationModal = false;
        this.redirectionObj = null;
        this.unlinkCalendarEvent = useUnlinkCalendarEvent({ model: this.model });
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

    /**
     * This method is meant to be overridden.
     */
    getInvitedAttendees(record, changes) {
        return (changes.partner_ids ?? []).reduce((acc, partner) => {
            if (partner[0] === 4) { // To only get the event's new partners and send them an invitation if needed.
                acc.push(partner[1]);
            }
            return acc;
        }, []);
    }

    /**
     * @override
     */
    async onRecordSaved(record, changes) {
        await super.onRecordSaved(...arguments);
        if (record.data.start >= luxon.DateTime.now()) {
            const invitedAttendees = this.getInvitedAttendees(record, changes);
            if (invitedAttendees.length > 0) {
                const actionOpenInviteWizard = await this.orm.call("calendar.event", "action_open_invite_wizard", [
                    record.resId,
                    invitedAttendees,
                    this.redirectionObj ? { "type": "ir.actions.act_url", "url": this.redirectionObj.url, "target": "self" } : null,
                ]);
                if (actionOpenInviteWizard && actionOpenInviteWizard.type) {
                    this.isPostSaveNotificationModal = true; // To not perform the redirection at the end of the saving but after the notification modal submission.
                    this.actionService.doAction(actionOpenInviteWizard);
                }
            }
        }
    }

    /**
     * @override
     */
    async onWillSaveRecord(record, changes) {
        user.updateContext({ disable_auto_send_invitation_emails : true });
        super.onWillSaveRecord(...arguments);
    }
}
