import { Component, useState } from "@odoo/owl";

const numberRange = (min, max) => [...Array(max - min)].map((_, i) => i + min);

const HOURS = numberRange(0, 24).map((hour) => [hour, String(hour)]);
const MINUTES = numberRange(0, 60).map((minute) => [minute, String(minute || 0).padStart(2, "0")]);

export class FloatTimeSelectionPopover extends Component {
    static props = {
        close: { type: Function },
        onTimeChange: { type: Function },
        timeValues: {
            type: Object,
            shape: {
                hours: "00",
                minutes: "00",
                floatValue: 0,
            },
        },
    };

    static template = "hr_holidays.FloatTimeSelectionPopover";

    setup() {
        this.availableHours = HOURS;
        this.availableMinutes = MINUTES;
        this.state = useState({
            selectedHours: this.props.timeValues.hours,
            selectedMinutes: this.props.timeValues.minutes,
        });
    }

    onTimeChange() {
        this.props.onTimeChange({
            hours: this.state.selectedHours,
            minutes: this.state.selectedMinutes,
        });
    }
}
