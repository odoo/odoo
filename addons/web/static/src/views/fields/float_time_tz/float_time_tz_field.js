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
 * displayed one is expressed in the user's timezone.
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

    parseValue(value) {
        return this.wrap(super.parseValue(value) - this.offset);
    }

    formatValue(value) {
        return super.formatValue(this.wrap(value + this.offset));
    }

    get formattedValue() {
        return this.value === false ? "" : this.formatValue(this.value);
    }
}

registry
    .category("fields")
    .add("float_time_tz", { ...floatTimeField, component: FloatTimeTzField });
