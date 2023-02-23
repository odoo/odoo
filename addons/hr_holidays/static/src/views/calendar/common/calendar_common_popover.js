/** @odoo-module */

import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";

import { useService } from "@web/core/utils/hooks";

export class TimeOffCalendarCommonPopover extends CalendarCommonPopover {
    setup() {
        super.setup();

        this.dialog = useService('dialog');
        this.action = useService('action');
    }

    get isEventDeletable() {
        const record = this.props.record.rawRecord;
        const state = record.state;
        return record.can_cancel || state && !['validate', 'refuse'].includes(state);
    }

    get isEventEditable() {
        const state = this.props.record.rawRecord.state;
        return state !== undefined;
    }
}
