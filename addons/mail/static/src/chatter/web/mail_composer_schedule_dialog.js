import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dialog } from "@web/core/dialog/dialog";
import { serializeDateTime, today } from "@web/core/l10n/dates";

import { Component, useState } from "@odoo/owl";

export class MailComposerScheduleDialog extends Component {
    static template = "mail.MailComposerScheduleDialog";
    static props = {
        close: Function,
        isNote: Boolean,
        schedule: Function,
    };
    static components = {
        DateTimeInput,
        Dialog,
    };

    setup() {
        const now = luxon.DateTime.now();
        this.state = useState({
            customDateTime: now
                .plus({ hours: 1 })
                .set({ minutes: Math.ceil(now.minute / 5) * 5, seconds: 0, milliseconds: 0 }),
            selectedOption: "morning",
        });
        this.dateTimeFormat = {
            day: "numeric",
            hour: "numeric",
            minute: "numeric",
            month: "short",
        };
    }

    get dateTimePickerProps() {
        return {
            minDate: luxon.DateTime.now(),
            onSelect: (value) => (this.state.customDateTime = value),
            type: "datetime",
            value: this.state.customDateTime,
        };
    }

    get mondayMorning() {
        return today()
            .plus({ days: (1 - today().weekday + 7) % 7 || 7 })
            .set({ hour: 8 });
    }

    get tomorrowAfternoon() {
        return today().plus({ days: 1 }).set({ hour: 13 });
    }

    get tomorrowMorning() {
        return today().plus({ days: 1 }).set({ hour: 8 });
    }

    get scheduledDate() {
        if (this.state.selectedOption === "morning") {
            return this.tomorrowMorning;
        } else if (this.state.selectedOption === "afternoon") {
            return this.tomorrowAfternoon;
        } else if (this.state.selectedOption === "monday") {
            return this.mondayMorning;
        } else {
            return this.state.customDateTime;
        }
    }

    async schedule() {
        await this.props.schedule(serializeDateTime(this.scheduledDate));
        this.props.close();
    }
}
