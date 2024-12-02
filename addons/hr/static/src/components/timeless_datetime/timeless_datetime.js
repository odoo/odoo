import { DateTimeField, dateTimeField } from "@web/views/fields/datetime/datetime_field";
import { formatDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";

class TimelessDateTimeField extends DateTimeField {
    /**
     * @override
     * @returns { Date }
     */
    getFormattedValue() {
        const { data } = this.props.record;
        return formatDate(data.create_date);
    }
}

export const timelessDateTimeField = {
    ...dateTimeField,
    component: TimelessDateTimeField,
};

registry.category("fields").add("timeless_datetime", timelessDateTimeField);
