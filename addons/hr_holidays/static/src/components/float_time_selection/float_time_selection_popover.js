import { Component, useState } from "@odoo/owl";
import { range } from "@web/core/utils/numbers";

const HOURS = range(24).map((hour) => [hour, String(hour)]);
const MINUTES = range(60).map((minute) => [minute, String(minute || 0).padStart(2, "0")]);

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
