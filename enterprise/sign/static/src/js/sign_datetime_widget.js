import { DateTimeField, dateTimeField } from '@web/views/fields/datetime/datetime_field';
import { formatDateTime } from '@web/core/l10n/dates';
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";

class DateTimeNoSeconds extends DateTimeField {
    static template = "sign.DateTimeNoSeconds";
    /**
     * @override
     * @returns { Date }
     */
    getFormattedValue() {
        const timeFormat = localization.dateTimeFormat.replace(":ss", "");
        const { data } = this.props.record;
        return formatDateTime(data.create_date, { format: timeFormat });
    }
}

export const dateTimeNoSeconds = {
    ...dateTimeField,
    component: DateTimeNoSeconds,
}

registry.category("fields").add('datetime_no_seconds', dateTimeNoSeconds);
