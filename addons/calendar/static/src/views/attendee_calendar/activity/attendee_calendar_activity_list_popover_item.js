import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { useService } from "@web/core/utils/hooks";

export class AttendeeCalendarActivityListPopoverItem extends ActivityListPopoverItem {
    static template = "calendar.AttendeeCalendarActivityListPopoverItem";
    static props = [...ActivityListPopoverItem.props, "onRemoveActivityItem"];

    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.orm = useService("orm");
    }

    /**
     * Remove the activity from the list when marking it as done.
     */
    onClickDone() {
        this.props.activity.remove();
        this.props.onRemoveActivityItem();
    }

    /**
     * Open the activity res record form view if user has access,
     * else open the activity form view.
     * In current window on click, in new window on middle click.
     */
    async onClickOpenResRecord(ev, isMiddleClick) {
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
        this.props.onRemoveActivityItem();
    }

    unlink() {
        super.unlink();
        this.props.onRemoveActivityItem();
    }
}
