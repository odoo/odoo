import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class AttendeeCalendarActivityListPopoverItem extends ActivityListPopoverItem {
    static components = {
        ...ActivityListPopoverItem.components,
        Dropdown,
        DropdownItem,
    };
    static template = "calendar.AttendeeCalendarActivityListPopoverItem";
    static props = [...ActivityListPopoverItem.props, "onRemoveActivityItem", "onViewMeeting"];

    setup() {
        super.setup(...arguments);
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
        return this.props.activity.calendar_event_id;
    }

    /**
     * Remove the activity from the list when marking it as done.
     */
    onClickDone() {
        this.props.activity.remove();
        this.props.onRemoveActivityItem(this.props.activity.id);
    }

    /**
     * Open the activity related record form view if user has access,
     * else open the activity form view.
     * In current window on click, in new window on middle click.
     */
    async onClickOpenRelatedRecord(ev, isMiddleClick) {
        const action = await this.orm.call("mail.activity", "action_open_document", [
            this.props.activity.id,
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
        await super.onFileUploaded(data);
        this.props.activity.remove();
        this.props.onRemoveActivityItem(this.props.activity.id);
    }

    /**
     * Reschedule the activity to a specific date.
     * @param {Object} targetDay
     */
    onRescheduleActivity(targetDay) {
        // Do nothing if rescheduled on same date.
        if (targetDay.day.hasSame(this.props.activity.date_deadline, "day")) {
            return;
        }
        this.action.doActionButton({
            type: "object",
            name: targetDay.actionName,
            resModel: "mail.activity",
            resId: this.props.activity.id,
            onClose: () => {
                this.props.activity.remove();
                this.props.onRemoveActivityItem(this.props.activity.id);
                this.props.onActivityChanged?.();
            },
        });
    }
}
