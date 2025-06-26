import { onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { FloatTimeSelectionPopover } from "./float_time_selection_popover";

import { FloatTimeField, floatTimeField } from "@web/views/fields/float_time/float_time_field";

function floatToHoursMinutes(floatValue) {
    const hours = Math.floor(floatValue);
    const minutes = Math.round((floatValue - hours) * 60);
    return { hours: String(hours).padStart(2, "0"), minutes: String(minutes).padStart(2, "0") };
}

function hoursMinutesToFloat(hours, minutes) {
    return parseInt(hours) + minutes / 60;
}

export class FloatTimeSelectionField extends FloatTimeField {
    static template = "hr_holidays.FloatTimeSelectionField";
    static props = {
        ...FloatTimeField.props,
    };

    setup() {
        super.setup();
        this.popover = usePopover(FloatTimeSelectionPopover, {
            onClose: this.onClose.bind(this),
        });
        this.timeValues = useState({
            hours: "00",
            minutes: "00",
            floatValue: 0,
        });

        onWillStart(() => {
            const initialValue = this.props.record.data[this.props.name];
            const { hours, minutes } = floatToHoursMinutes(initialValue);
            this.timeValues.hours = hours;
            this.timeValues.minutes = minutes;
            this.timeValues.floatValue = initialValue;
        });
    }

    onCharHoursClick(ev) {
        ev.preventDefault();
        this.popover.open(ev.currentTarget, {
            timeValues: this.timeValues,
            onTimeChange: this.onTimeChange.bind(this),
        });
        setTimeout(() => {
            this.inputFloatTimeRef.el.focus(); // focus on the input rather than the popover
        }, 0);
    }

    onTimeChange(newTimeValues) {
        this.timeValues.hours = newTimeValues.hours;
        this.timeValues.minutes = newTimeValues.minutes;
        this.timeValues.floatValue = parseInt(newTimeValues.hours) + newTimeValues.minutes / 60;
    }

    handleInputChange() {
        this.popover.close();
        const inputValue = this.inputFloatTimeRef.el.value;
        const [hours, minutes] = inputValue.split(":").map(Number);
        if (!isNaN(hours) && !isNaN(minutes)) {
            this.timeValues.hours = String(hours).padStart(2, "0");
            this.timeValues.minutes = String(minutes).padStart(2, "0");
            this.timeValues.floatValue = hoursMinutesToFloat(hours, minutes);
        } else {
            const { hours, minutes } = floatToHoursMinutes(parseFloat(inputValue));
            this.timeValues.hours = hours;
            this.timeValues.minutes = minutes;
            this.timeValues.floatValue = parseFloat(inputValue);
        }
    }

    onClose() {
        this.props.record.update({ [this.props.name]: this.timeValues.floatValue });
    }
}

export const charHours = {
    ...floatTimeField,
    component: FloatTimeSelectionField,
};

registry.category("fields").add("float_time_selection", charHours);
