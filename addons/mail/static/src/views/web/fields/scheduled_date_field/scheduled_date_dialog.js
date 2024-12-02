import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dialog } from "@web/core/dialog/dialog";
import { today } from "@web/core/l10n/dates";

import { Component, useState } from "@odoo/owl";

export class ScheduledDateDialog extends Component {
    static template = "mail.ScheduledDateDialog";
    static props = {
        close: Function,
        isRemovable: { type: Boolean },
        save: Function,
        scheduledDate: { type: luxon.DateTime, optional: true },
    };
    static components = {
        DateTimeInput,
        Dialog,
    };

    setup() {
        const now = luxon.DateTime.now();
        this.tomorrowMorning = today().plus({ days: 1 }).set({ hour: 8 });
        this.tomorrowAfternoon = this.tomorrowMorning.set({ hour: 13 });
        this.mondayMorning = today()
            .plus({ days: (1 - today().weekday + 7) % 7 || 7 })
            .set({ hour: 8 });

        this.state = useState({
            customDateTime: now
                .plus({ hours: 1 })
                .set({ minutes: Math.ceil(now.minute / 5) * 5, seconds: 0, milliseconds: 0 }),
            selectedOption: undefined,
        });

        if (!this.props.scheduledDate || this.props.scheduledDate.equals(this.tomorrowMorning)) {
            this.state.selectedOption = "morning";
        } else if (this.props.scheduledDate.equals(this.tomorrowAfternoon)) {
            this.state.selectedOption = "afternoon";
        } else if (this.props.scheduledDate.equals(this.mondayMorning)) {
            this.state.selectedOption = "monday";
        } else {
            this.state.selectedOption = "custom";
            this.state.customDateTime = this.props.scheduledDate;
        }
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

    clear() {
        this.props.save(false);
        this.props.close();
    }

    save() {
        this.props.save(this.scheduledDate);
        this.props.close();
    }
}
