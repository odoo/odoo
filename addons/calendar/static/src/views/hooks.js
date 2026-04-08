import { useDeleteRecords } from "@web/views/view_hook";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

/**
 * Display a composer containing the cancellation template email if required. The event is declined if the user is a regular attendee.
 */
export function useDeleteCalendarEvent({ model }) {
    const actionService = useService("action");
    if (!model.dialog) {
        model.dialog = useService("dialog");  // To get the default values of the delete confirmation dialog.
    }
    const deleteRecordWithConfirmation = useDeleteRecords(model);
    const orm = useService("orm");

    return async ({ resId, currentAttendeeId, currentStatus, organizerId, partnerIds, recurrency, start, deleteConfirmationDialogProps, nextAction }) => {
        if (user.isAdmin || user.userId === organizerId) {
            if (
                start >= luxon.DateTime.now()
                && (recurrency || !(partnerIds.length === 1 && partnerIds[0] === user.partnerId))
            ) {
                const actionUnlink = await orm.call("calendar.event", "action_unlink", [resId, currentAttendeeId, nextAction]);
                if (actionUnlink && actionUnlink.type) {
                    return actionService.doAction(actionUnlink);
                };
            } else {
                deleteRecordWithConfirmation(deleteConfirmationDialogProps);
            }
        } else if (currentAttendeeId && currentStatus !== "declined") {
            await orm.call("calendar.attendee", "do_decline", [currentAttendeeId]);
            return actionService.doAction("soft_reload");
        }
    }
}

/**
 * Display modals to send cancellation emails or chose the deletion type for recurring events.
 */
export function useDeleteCalendarEvents({ model }) {
    const actionService = useService("action");
    if (!model.dialog) {
        model.dialog = useService("dialog");  // To get the default values of the delete confirmation dialog.
    }
    const deleteRecordWithConfirmation = useDeleteRecords(model);
    const orm = useService("orm");

    return async ({ records, deleteConfirmationDialogProps }) => {
        const declinedAttendeeIds = [];
        let isUnlinkActionRequired = false;
        const unlinkActionEventIds = [];
        const now = luxon.DateTime.now();
        for (const record of records) {
            if (user.isAdmin || user.userId === record.data.user_id.id) {
                unlinkActionEventIds.push(record.resId);
                const partnerIds = record.data.partner_ids.resIds;
                if (
                    record.data.start >= now
                    && (record.data.recurrency || !(partnerIds.length === 1 && partnerIds[0] === user.partnerId))
                ) {
                    isUnlinkActionRequired = true;
                }
            } else {
                record.selected = false;
                if (record.data.current_attendee && record.data.current_status !== "declined") {
                    declinedAttendeeIds.push(record.data.current_attendee.id);
                }
            }
        }
        if (declinedAttendeeIds.length > 0) {
            await orm.call("calendar.attendee", "do_decline", [declinedAttendeeIds]);
        }
        if (isUnlinkActionRequired) {
            const actionUnlink = await orm.call("calendar.event", "action_unlink", [unlinkActionEventIds]);
            if (actionUnlink && actionUnlink.type) {
                actionService.doAction(actionUnlink);
            }
        } else if (records.length > 0) {
            deleteRecordWithConfirmation(deleteConfirmationDialogProps);
        } else {
            actionService.doAction("soft_reload");
        }
    }
}
