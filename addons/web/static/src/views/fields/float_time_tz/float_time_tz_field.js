import { parseTime, is24HourFormat } from "@web/core/l10n/time";
import { registry } from "@web/core/registry";
import { FloatTimeField, floatTimeField } from "@web/views/fields/float_time/float_time_field";
import { user } from "@web/core/user";

const { DateTime } = luxon;

const DAY = {
    hours: 24,
    minutes: 24 * 60,
    seconds: 24 * 3600,
};

/**
 * Same as `float_time`, but the stored value is a UTC time of day while the
 * displayed one is expressed in the user's timezone and time format.
 */
export class FloatTimeTzField extends FloatTimeField {
    /**
     * The user's UTC offset, expressed in the unit of the field.
     */
    get offset() {
        const hours = DateTime.now().setZone(user.tz || "default").offset / 60;
        return (hours * DAY[this.props.unit]) / 24;
    }

    wrap(value) {
        const day = DAY[this.props.unit];
        return ((value % day) + day) % day;
    }

    // the displayed time is already in its final form, no preview needed
    onValueChange() {}
    openPopover() {}
    parseValue(value) {
        const { hour, minute } = parseTime(value);
        const localValue = ((hour * 60 + minute) * DAY[this.props.unit]) / DAY.minutes;
        return this.wrap(localValue - this.offset);
    }

    get formattedValue() {
        const value = this.props.record.data[this.props.name];
        if (value === false) {
            return "";
        }
        const minutes = Math.round(
            (this.wrap(value + this.offset) * DAY.minutes) / DAY[this.props.unit]
        );
        return DateTime.fromObject({ hour: 0 }, { zone: "utc" })
            .plus({ minutes })
            .toFormat(is24HourFormat() ? "HH:mm" : "hh:mm a");
    }
}

registry
    .category("fields")
    .add("float_time_tz", { ...floatTimeField, component: FloatTimeTzField });
