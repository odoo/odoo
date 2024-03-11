/** @odoo-module **/

import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { useService } from "@web/core/utils/hooks";
import { useAskRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class AttendeeCalendarCommonPopover extends CalendarCommonPopover {
    setup() {
        super.setup();
        this.user = useService("user");
        this.orm = useService("orm");
        this.askRecurrenceUpdatePolicy = useAskRecurrenceUpdatePolicy();
        // Show status dropdown if user is in attendees list
        if (this.isCurrentUserAttendee) {
            this.statusColors = {
                accepted: "text-success",
                declined: "text-danger",
                tentative: "text-muted",
                needsAction: "text-dark",
            };
            this.statusInfo = {};
            for (const selection of this.props.model.fields.attendee_status.selection) {
                this.statusInfo[selection[0]] = {
                    text: selection[1],
                    color: this.statusColors[selection[0]],
                };
            }
            this.selectedStatusInfo = this.statusInfo[this.props.record.attendeeStatus];
        }
    }

    get isCurrentUserAttendee() {
        return this.props.record.rawRecord.partner_ids.includes(this.user.partnerId);
    }

    get isCurrentUserOrganizer() {
        return this.props.record.rawRecord.partner_id[0] === this.user.partnerId;
    }

    get isEventPrivate() {
        return this.props.record.rawRecord.privacy === "private";
    }

    get displayAttendeeAnswerChoice() {
        return (
            this.props.record.rawRecord.partner_ids.some((partner) => partner !== this.user.partnerId) &&
            this.props.record.isCurrentPartner
        );
    }

    get isEventDetailsVisible() {
        return this.isEventPrivate ? this.isCurrentUserAttendee : true;
    }

    get isEventArchivable() {
        return false;
    }

    /**
     * @override
     */
    get isEventDeletable() {
        return super.isEventDeletable && this.isCurrentUserAttendee && !this.isEventArchivable;
    }

    /**
     * @override
     */
    get isEventEditable() {
        return this.isEventPrivate ? this.isCurrentUserAttendee : super.isEventEditable;
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
        await this.env.services.orm.call(
            this.props.model.resModel,
            "change_attendee_status",
            [[record.id], selectedStatus, recurrenceUpdate],
        );
        await this.props.model.load();
        this.props.close();
    }

    async onClickArchive() {
        await this.props.model.archiveRecord(this.props.record);
    }
}
AttendeeCalendarCommonPopover.components = {
    ...CalendarCommonPopover.components,
    Dropdown,
    DropdownItem,
};
AttendeeCalendarCommonPopover.subTemplates = {
    ...CalendarCommonPopover.subTemplates,
    body: "calendar.AttendeeCalendarCommonPopover.body",
    footer: "calendar.AttendeeCalendarCommonPopover.footer",
};
