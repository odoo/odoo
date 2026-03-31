import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { FileUploader } from "@web/views/fields/file_handler";
import { getFormattedDateSpan } from "@web/views/calendar/utils";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { useRef, useState } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";

import { Component, onPatched } from "@odoo/owl";

const { DateTime } = luxon;

export class AttendeeCalendarActivityPopover extends Component {
    static template = "web.CalendarCommonPopover";
    static subTemplates = {
        popover: "web.CalendarCommonPopover.popover",
        body: "calendar.AttendeeCalendarActivityPopover.body",
        footer: "calendar.AttendeeCalendarActivityPopover.footer",
    };
    static components = {
        Dialog,
        Dropdown,
        DropdownItem,
        FileUploader,
    };
    static props = {
        close: Function,
        model: Object,
        // Full calendar activity event record, used for header rendering.
        record: Object,
        // Activity record, used for body and footer rendering.
        activity: Object,
        onViewMeeting: Function,
    };

    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
        // Mark Done
        this.state = useState({ hasMarkDoneView: false });
        this.feedbackTextArea = useRef("textarea");
        onPatched(() => this.feedbackTextArea.el?.focus());
        // Reschedule
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
        // File Upload
        if (this.props.activity.activity_category === "upload_file") {
            this.attachmentUploader = useAttachmentUploader(
                this.env.services["mail.store"]["mail.thread"].insert({
                    model: this.props.activity.res_model,
                    id: this.props.activity.res_id,
                })
            );
        }
    }

    get formattedDate() {
        const activity = this.props.activity;
        return getFormattedDateSpan(activity.date_deadline, activity.date_deadline);
    }

    get hasEditButton() {
        return this.props.activity.can_write && !this.hasViewMeetingButton;
    }

    get hasFileUploadButton() {
        const activity = this.props.activity;
        return activity.can_write && activity.activity_category === "upload_file";
    }

    get hasFooter() {
        return this.props.activity.can_write || this.props.activity.calendar_event_id;
    }

    get hasMarkDoneButton() {
        return this.props.activity.can_write && !this.hasFileUploadButton;
    }

    get hasRescheduleButton() {
        return this.props.activity.can_write;
    }

    get hasViewMeetingButton() {
        return this.props.activity.calendar_event_id;
    }

    /**
     * Mark activity as done (with feedback if any specified).
     */
    async onClickDone() {
        await this.props.activity.markAsDone();
        this.props.model.load();
        this.props.close();
    }

    /**
     * Mark activity as done (with feedback if any specified)
     * and open a new form in a modal to schedule another activity on the related record.
     */
    async onClickDoneAndScheduleNext() {
        const action = await this.props.activity.markAsDoneAndScheduleNext();
        this.action.doAction(action, {
            onClose: () => this.props.model.load(),
        });
        this.props.close();
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
        this.props.close();
    }

    /**
     * Open the activity form view in a modal.
     */
    onEditActivity() {
        this.props.activity.edit().then(() => this.props.model.load());
        this.props.close();
    }

    /**
     * Upload file and mark activity as done.
     * Relevant for activity of type "Document".
     */
    async onFileUploaded(data) {
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data, {
            activity: this.props.activity,
        });
        await this.props.activity.markAsDone([attachmentId]);
        this.props.model.load();
        this.props.close();
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
                this.props.model.load();
                this.props.close();
            },
        });
    }
}
