import { Component, useEffect, useState } from "@odoo/owl";
import { range } from "@web/core/utils/numbers";

const HOURS = range(24).map((hour) => [hour, String(hour)]);
const MINUTES = range(60).map((minute) => [minute, String(minute || 0).padStart(2, "0")]);

export class HourTimeSelectionPopover extends Component {
    static props = {
        close: { type: Function, optional: true },
        onTimeChange: { type: Function },
        timeValues: {
            type: Object,
            shape: {
                hours: String,
                minutes: String,
                floatValue: Number,
            },
        },
    };

    static template = "hr_holidays.HourTimeSelectionPopover";

    setup() {
        this.availableHours = HOURS;
        this.availableMinutes = MINUTES;
        this.state = useState({
            selectedHours: this.props.timeValues.hours,
            selectedMinutes: this.props.timeValues.minutes,
        });

        useEffect(
            () => {
                this.state.selectedHours = this.props.timeValues.hours;
                this.state.selectedMinutes = this.props.timeValues.minutes;
            },
            () => [this.props.timeValues.hours, this.props.timeValues.minutes]
        );
    }

    onTimeChange() {
        this.props.onTimeChange({
            hours: this.state.selectedHours,
            minutes: this.state.selectedMinutes,
        });
    }
}
