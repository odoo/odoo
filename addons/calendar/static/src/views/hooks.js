import { useDeleteRecords } from "@web/views/view_hook";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

function shouldUseUnlinkWizard(now, partnerIds, recurrency, start) {
    return (
        start >= now
        && (recurrency || !(partnerIds.length === 1 && partnerIds[0] === user.partnerId))
    )
}

/**
 * If required, this method allows to handle steps related to the event's deletion from the frontend. It opens either a
 * form to edit and send the cancellation email or a form allowing to select which events of the event's recurrence must
 * be deleted.
 */
export function useUnlinkCalendarEvent() {
    const actionService = useService("action");
    const orm = useService("orm");

    return async ({ resId, partnerIds, recurrency, start, defaultAction, nextAction }) => {
        if (shouldUseUnlinkWizard(luxon.DateTime.now(), partnerIds, recurrency, start)) {
            const actionOpenUnlinkWizard = await orm.call(
                "calendar.event",
                "action_open_unlink_wizard",
                [resId, nextAction]
            );
            if (actionOpenUnlinkWizard) {
                actionService.doAction(actionOpenUnlinkWizard);
            }
        } else {
            defaultAction();
        }
    }
}

/**
 * Display modals to send cancellation emails or chose the deletion type for recurring events.
 */
export function useUnlinkCalendarEvents() {
    const actionService = useService("action");
    const orm = useService("orm");

    return async ({ records, defaultAction }) => {
        let isUnlinkWizardRequired = false;
        const now = luxon.DateTime.now();
        for (const record of records) {
            const { data } = record;
            if (shouldUseUnlinkWizard(now, data.partner_ids.resIds, data.recurrency, data.start)) {
                isUnlinkWizardRequired = true;
                break;
            }
        }
        if (isUnlinkWizardRequired) {
            const actionOpenUnlinkWizard = await orm.call(
                "calendar.event",
                "action_open_unlink_wizard",
                [records.map(record => record.resId)]
            );
            if (actionOpenUnlinkWizard) {
                actionService.doAction(actionOpenUnlinkWizard);
            }
        } else {
            defaultAction();
        }
    }
}
