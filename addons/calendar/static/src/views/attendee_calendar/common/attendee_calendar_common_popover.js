import { onWillStart } from "@odoo/owl";
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

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        if (this.isEventEditable) {
            const stateSelections = await this.env.services.orm.call(
                this.props.model.resModel,
                "get_state_selections"
            );
            this.statusColors = {
                accepted: "text-success",
                declined: "text-danger",
                tentative: "text-muted",
                needsAction: "false",
            };
            this.statusInfo = {};
            for (const selection of stateSelections) {
                this.statusInfo[selection[0]] = {
                    text: selection[1],
                    color: this.statusColors[selection[0]],
                };
            }
            this.selectedStatusInfo = this.statusInfo[this.props.record.attendeeStatus];
        }
    }

    get isCurrentUserAttendee() {
        return (
            this.props.record.rawRecord.partner_ids.includes(user.partnerId) ||
            this.props.record.rawRecord.partner_id[0] === user.partnerId
        );
    }

    get isCurrentUserOrganizer() {
        return this.props.record.rawRecord.partner_id[0] === user.partnerId;
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

    get isEventDetailsVisible() {
        return this.isEventPrivate ? this.isEventEditable : true;
    }

    get isEventArchivable() {
        return false;
    }

    get isEventDeletable() {
        return super.isEventDeletable && this.isEventEditable && !this.isEventArchivable;
    }

    get isEventEditable() {
        return this.props.record.rawRecord.user_can_edit;
    }

    get isEventViewable() {
        return this.isEventPrivate ? this.isEventEditable : super.isEventEditable;
    }

    async changeAttendeeStatus(selectedStatus) {
        if (this.props.record.attendeeStatus === selectedStatus) {
            return this.props.close();
        }
        let recurrenceUpdate = false;
        if (this.props.record.rawRecord.recurrency) {
            recurrenceUpdate = await this.askRecurrenceUpdatePolicy();
            if (!recurrenceUpdate) {
                return this.props.close();
            }
        }
        await this.env.services.orm.call(this.props.model.resModel, "change_attendee_status", [
            [this.props.record.id],
            selectedStatus,
            recurrenceUpdate,
        ]);
        await this.props.model.load();
        this.props.close();
    }

    async onClickArchive() {
        this.props.close();
        await this.props.model.archiveRecord(this.props.record);
    }
}
