import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

/**
 * Display a composer containing the cancellation template email if required. The event is declined if the user is a regular attendee.
 */
export function useCancelCalendarEvent() {
    const actionService = useService("action");
    const orm = useService("orm");

    return async ({ requestedAction, resId, currentAttendeeId, currentStatus, isDraft, organizerId, partnerIds, recurrency, start, fallback, nextAction }) => {
        if (user.isAdmin || user.userId === organizerId) {
            if (
                start >= luxon.DateTime.now()
                && !isDraft
                && (recurrency || !(partnerIds.length === 1 && partnerIds[0] === user.partnerId))
            ) {
                const actionOpenCancelWizard = await orm.call("calendar.event", "action_open_cancel_wizard", [resId, requestedAction, currentAttendeeId, nextAction]);
                if (actionOpenCancelWizard && actionOpenCancelWizard.type) {
                    return actionService.doAction(actionOpenCancelWizard);
                }
            } else {
                fallback();
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
export function useCancelCalendarEvents() {
    const actionService = useService("action");
    const orm = useService("orm");

    return async ({ requestedAction, records, fallback }) => {
        const declinedAttendeeIds = [];
        let isCancelWizardRequired = false;
        const cancelWizardEventIds = [];
        const now = luxon.DateTime.now();
        for (const record of records) {
            if (user.isAdmin || user.userId === record.data.user_id.id) {
                cancelWizardEventIds.push(record.resId);
                const partnerIds = record.data.partner_ids.resIds;
                if (
                    record.data.start >= now
                    && !record.data.is_draft
                    && (record.data.recurrency || !(partnerIds.length === 1 && partnerIds[0] === user.partnerId))
                ) {
                    isCancelWizardRequired = true;
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
        if (isCancelWizardRequired) {
            const actionOpenCancelWizard = await orm.call("calendar.event", "action_open_cancel_wizard", [cancelWizardEventIds, requestedAction]);
            if (actionOpenCancelWizard && actionOpenCancelWizard.type) {
                actionService.doAction(actionOpenCancelWizard);
            }
        } else if (records.length > 0) {
            fallback();
        } else {
            actionService.doAction("soft_reload");
        }
    }
}
