import { registry } from "@web/core/registry";
import {_t} from "@web/core/l10n/translation";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";

export class TimeHourField extends FloatTimeField {
    get formattedValue() {
        const unitAmount = super.formattedValue;
        const [hourStr, minuteStr] = unitAmount.split(":");
        const hours = parseInt(hourStr, 10);
        const minutes = parseInt(minuteStr, 10);
        return minutes ? _t("%(hours)sh%(minutes)s", { hours, minutes }) : _t("%(hours)sh", { hours });
    }
}
export const timeHourField = {
    component: TimeHourField,
};

registry.category("fields").add("time_hour_uom", timeHourField);
