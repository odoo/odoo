import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormController } from "@web/views/form/form_controller";
import { useCancelCalendarEvent } from "@calendar/views/hooks";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class CalendarFormController extends FormController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.cancelCalendarEvent = useCancelCalendarEvent();
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (actionMenuItems.archive.isAvailable) {
            actionMenuItems.archive.callback = async () => {
                const record = this.model.root;
                await this.cancelCalendarEvent({
                    requestedAction: "cancel",
                    resId: record.resId,
                    currentAttendeeId: record.data.current_attendee.id,
                    currentStatus: record.data.current_status,
                    isDraft: record.data.is_draft,
                    organizerId: record.data.user_id.id,
                    partnerIds: record.data.partner_ids.resIds,
                    recurrency: record.data.recurrency,
                    start: record.data.start,
                    fallback: () => this.dialogService.add(ConfirmationDialog, this.archiveDialogProps),
                });
            };
        }
        return actionMenuItems;
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
        await this.cancelCalendarEvent({
            requestedAction: "delete",
            resId: record.resId,
            currentAttendeeId: record.data.current_attendee.id,
            currentStatus: record.data.current_status,
            isDraft: record.data.is_draft,
            organizerId: record.data.user_id.id,
            partnerIds: record.data.partner_ids.resIds,
            recurrency: record.data.recurrency,
            start: record.data.start,
            fallback: () => this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps),
            nextAction: { type: "ir.actions.act_url", target: "self", url: "/odoo/calendar" },
        });
    }

    /**
     * This method is meant to be overridden.
     */
    getInvitedAttendees(record, changes) {
        return (changes.partner_ids ?? []).reduce((acc, partner) => {
            if (partner[0] === 4) {
                acc.push(partner[1]);
            }
            return acc;
        }, []);
    }

    /**
     * This method is meant to be overridden.
     */
    canNotifyAttendees(record, changes) {
        return !record.data.is_draft;
    }

    /**
     * This method is meant to be overridden.
     */
    async notifyAttendees(record, changes) {
        const invitedAttendees = this.getInvitedAttendees(record, changes);
        if (invitedAttendees.length > 0) {
            const actionOpenInviteWizard = await this.orm.call("calendar.event", "action_open_invite_wizard", [
                record.resId,
                invitedAttendees,
                null,
                this.props.redirectionObj ? { "type": "ir.actions.act_url", "url": this.props.redirectionObj.url, "target": "self" } : null,
            ]);
            if (actionOpenInviteWizard && actionOpenInviteWizard.type) {
                this.props.isPostSaveNotificationModal = true; // To not perform the redirection at the end of the saving but after the notification modal submission.
                this.actionService.doAction(actionOpenInviteWizard);
            }
        }
    }

    /**
     * @override
     */
    async onRecordSaved(record, changes) {
        await super.onRecordSaved(...arguments);
        if (record.data.start >= luxon.DateTime.now() && this.canNotifyAttendees(record, changes)) {
            await this.notifyAttendees(record, changes);
        }
    }

    /**
     * @override
     */
    async onWillSaveRecord(record, changes) {
        user.updateContext({ block_automatic_invitation_email : true });
        super.onWillSaveRecord(...arguments);
    }
}
