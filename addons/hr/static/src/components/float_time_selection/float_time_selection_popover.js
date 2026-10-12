import { Component, proxy, t, useProps } from "@odoo/owl";
import { range } from "@web/core/utils/numbers";

const HOURS = range(24).map((hour) => [hour, String(hour)]);
const MINUTES = range(60).map((minute) => [minute, String(minute || 0).padStart(2, "0")]);

export class FloatTimeSelectionPopover extends Component {
    static template = "hr.FloatTimeSelectionPopover";

    props = useProps({
        close: t.function(),
        onTimeChange: t.function(),
        timeValues: t.object({
            hours: t.string(),
            minutes: t.string(),
            floatValue: t.number(),
        }),
    });

    setup() {
        this.availableHours = HOURS;
        this.availableMinutes = MINUTES;
        this.state = proxy({
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
