/** @odoo-module **/

import { Component } from "@odoo/owl";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { DateTimeField } from "../datetime/datetime_field";
import { standardFieldProps } from "../standard_field_props";

const { DateTime } = luxon;

export class RemainingDaysField extends Component {
    static components = { DateTimeField };

    static props = standardFieldProps;

    static template = "web.RemainingDaysField";

    get diffDays() {
        const { record, name } = this.props;
        const value = record.data[name];
        if (!value) {
            return null;
        }
        const today = DateTime.local().startOf("day");
        const diff = value.startOf("day").diff(today, "days");
        return Math.floor(diff.days);
    }

    get formattedValue() {
        const { record, name } = this.props;
        return record.fields[name].type === "datetime"
            ? formatDateTime(record.data[name], { format: localization.dateFormat })
            : formatDate(record.data[name]);
    }
}

export const remainingDaysField = {
    component: RemainingDaysField,
    displayName: _lt("Remaining Days"),
    supportedTypes: ["date", "datetime"],
};

registry.category("fields").add("remaining_days", remainingDaysField);
