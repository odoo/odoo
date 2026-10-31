import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { useService } from "@web/core/utils/hooks";
import { useAskRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { user } from "@web/core/user";

export class AttendeeCalendarCommonPopover extends CalendarCommonPopover {
    static components = {
        ...CalendarCommonPopover.components,
        Dropdown,
        DropdownItem,
    };
    static defaultFooterButtonsTemplate = "calendar.AttendeeCalendarCommonPopover.footer";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.askRecurrenceUpdatePolicy = useAskRecurrenceUpdatePolicy();
    }

    get isCurrentUserAttendee() {
        return (
            this.props.record.rawRecord.partner_ids.includes(user.partnerId) ||
            this.props.record.rawRecord.partner_id[0] === user.partnerId
        );
    }

    get isEventPrivate() {
        return this.props.record.rawRecord.privacy === "private";
    }

    get displayAttendeeAnswerChoice() {
        return (
            this.props.record.rawRecord.partner_ids.some((partner) => partner !== user.partnerId) &&
            this.props.record.isCurrentPartner
        );
    }

    /**
     * @override
     */
    get isEventDeletable() {
        return super.isEventDeletable && this.isEventEditable;
    }

    /**
     * @override
     */
    get isEventEditable() {
        return this.props.record.rawRecord.user_can_edit;
    }

    get isEventViewable() {
        return this.isEventPrivate ? this.isEventEditable : super.isEventEditable;
    }

    async changeAttendeeStatus(selectedStatus) {
        const record = this.props.record;
        if (record.attendeeStatus === selectedStatus) {
            return this.props.close();
        }
        let recurrenceUpdate = false;
        if (record.rawRecord.recurrency) {
            recurrenceUpdate = await this.askRecurrenceUpdatePolicy();
            if (!recurrenceUpdate) {
                return this.props.close();
            }
        }
        await this.env.services.orm.call(this.props.model.resModel, "change_attendee_status", [
            [record.id],
            selectedStatus,
            recurrenceUpdate,
        ]);
        await this.props.model.load();
        this.props.close();
    }
}
