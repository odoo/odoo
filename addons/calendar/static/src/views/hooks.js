import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

function shouldUseArchiveOrUnlinkWizard(isDraft, now, partnerIds, recurrency, start) {
    return (
        start >= now
        && !isDraft
        && (recurrency || !(partnerIds.length === 1 && partnerIds[0] === user.partnerId))
    )
}

/**
 * If required, this method allows to handle steps related to the event's archiving or deletion from the frontend. It
 * opens either a form to edit and send the cancellation email or a form allowing to select which events of the event's
 * recurrence must be archived or deleted.
 */
export function useArchiveOrUnlinkCalendarEvent() {
    const actionService = useService("action");
    const orm = useService("orm");

    return async ({ requestedAction, resId, isDraft, partnerIds, recurrency, start, defaultAction, nextAction }) => {
        if (shouldUseArchiveOrUnlinkWizard(isDraft, luxon.DateTime.now(), partnerIds, recurrency, start)) {
            const actionOpenArchiveOrUnlinkWizard = await orm.call(
                "calendar.event",
                "action_open_archive_or_unlink_wizard",
                [resId, requestedAction, nextAction]
            );
            if (actionOpenArchiveOrUnlinkWizard) {
                actionService.doAction(actionOpenArchiveOrUnlinkWizard);
            }
        } else {
            defaultAction();
        }
    }
}

/**
 * Display modals to send cancellation emails or select the events to delete or archive in the recurrency.
 */
export function useArchiveOrUnlinkCalendarEvents() {
    const actionService = useService("action");
    const orm = useService("orm");

    return async ({ requestedAction, records, defaultAction }) => {
        let isArchiveOrUnlinkWizardRequired = false;
        const now = luxon.DateTime.now();
        for (const record of records) {
            const { data } = record;
            if (shouldUseArchiveOrUnlinkWizard(data.is_draft, now, data.partner_ids.resIds, data.recurrency, data.start)) {
                isArchiveOrUnlinkWizardRequired = true;
                break;
            }
        }
        if (isArchiveOrUnlinkWizardRequired) {
            const actionOpenArchiveOrUnlinkWizard = await orm.call(
                "calendar.event",
                "action_open_archive_or_unlink_wizard",
                [records.map(record => record.resId), requestedAction]
            );
            if (actionOpenArchiveOrUnlinkWizard) {
                actionService.doAction(actionOpenArchiveOrUnlinkWizard);
            }
        } else {
            defaultAction();
        }
    }
}
