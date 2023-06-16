/* @odoo-module */

import { FloatTimeField, floatTimeField } from "@web/views/fields/float_time/float_time_field";
import { registry } from "@web/core/registry";
import { _t } from "web.core";

class LivechatDurationField extends FloatTimeField {
    get formattedValue() {
        return `${super.formattedValue} ${_t("min")}`;
    }
}

registry.category("fields").add("duration_field", {
    ...floatTimeField,
    component: LivechatDurationField,
});
