import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

import { props, types } from "@odoo/owl";

const { DateTime } = luxon;

/** @param {import("models").Store} store */
export const onViewMeetingType = (store) =>
    types.function([
        types.instanceOf(MouseEvent),
        types.object({ eventAtRender: types.instanceOf(store["calendar.event"].Class) }),
    ]);

export class AttendeeCalendarActivityListPopoverItem extends ActivityListPopoverItem {
    static components = {
        ...ActivityListPopoverItem.components,
        Dropdown,
        DropdownItem,
    };
    static template = "calendar.AttendeeCalendarActivityListPopoverItem";

    setup() {
        super.setup(...arguments);
        // bound once so `onClickDone` is a stable (props.static) handler
        this.onClickDone = this.onClickDone.bind(this);
        this.calendarProps = props({
            onRemoveActivityItem: types.function([types.number()]),
            onViewMeeting: onViewMeetingType(this.store),
        });
        this.action = useService("action");
        this.orm = useService("orm");
        const today = DateTime.now().startOf("day");
        this.targetDays = {
            today: {
                day: today,
                actionName: "action_reschedule_today",
            },
            tomorrow: {
                day: today.plus({ days: 1 }),
                actionName: "action_reschedule_tomorrow",
            },
            nextWeek: {
                day: today.plus({ weeks: 1 }).startOf("week"),
                actionName: "action_reschedule_nextweek",
            },
        };
    }

    get hasCancelButton() {
        return false;
    }

    /**
     * Remove the “Reschedule Meeting” button, as this component is already
     * in the calendar view (no need for the action redirection) and provides its own
     * “Reschedule Activity” dropdown which automatically updates the activity
     * and its related meeting.
     */
    get hasRescheduleMeetingButton() {
        return false;
    }

    get hasViewMeetingButton() {
        return this.activity().calendar_event_id;
    }

    /**
     * Remove the activity from the list when marking it as done.
     */
    onClickDone() {
        this.activity().remove();
        this.calendarProps.onRemoveActivityItem(this.activity().id);
    }

    /**
     * Open the activity related record form view if user has access,
     * else open the activity form view.
     * In current window on click, in new window on middle click.
     */
    async onClickOpenRelatedRecord(ev, isMiddleClick) {
        const action = await this.orm.call("mail.activity", "action_open_document", [
            this.activity().id,
        ]);
        this.action.doAction(action, {
            newWindow: isMiddleClick,
        });
    }

    /**
     * Remove the activity from the list when uploading a document
     * (i.e. when an activity of type Document is marked as done).
     */
    async onFileUploaded(data) {
        const activity = this.activity();
        await super.onFileUploaded(data);
        activity.remove();
        this.calendarProps.onRemoveActivityItem(activity.id);
    }

    /**
     * Reschedule the activity to a specific date.
     * @param {Object} targetDay
     */
    onRescheduleActivity(targetDay) {
        // Do nothing if rescheduled on same date.
        if (targetDay.day.hasSame(this.activity().date_deadline, "day")) {
            return;
        }
        const activity = this.activity();
        this.action.doActionButton({
            type: "object",
            name: targetDay.actionName,
            resModel: "mail.activity",
            resId: activity.id,
            onClose: () => {
                activity.remove();
                this.calendarProps.onRemoveActivityItem(activity.id);
                this.onActivityChanged?.();
            },
        });
    }
}
