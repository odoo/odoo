/** @odoo-module **/

import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class RemainingDaysField extends Component {
    static template = "web.RemainingDaysField";
    static props = {
        ...standardFieldProps,
    };

    get hasTime() {
        return this.props.type === "datetime";
    }

    get pickerComponent() {
        return this.hasTime ? DateTimePicker : DatePicker;
    }

    get diffDays() {
        if (!this.props.value) {
            return null;
        }
        const today = luxon.DateTime.local().startOf("day");
        return Math.floor(this.props.value.startOf("day").diff(today, "days").days);
    }

    get formattedValue() {
        return this.hasTime
            ? formatDateTime(this.props.value, { format: localization.dateFormat })
            : formatDate(this.props.value);
    }

    onDateTimeChanged(datetime) {
        if (datetime) {
            this.props.record.update({ [this.props.name]: datetime });
        } else if (typeof datetime === "string") {
            // when the date is cleared
            this.props.record.update({ [this.props.name]: false });
        }
    }
}

export const remainingDaysField = {
    component: RemainingDaysField,
    displayName: _lt("Remaining Days"),
    supportedTypes: ["date", "datetime"],
};

registry.category("fields").add("remaining_days", remainingDaysField);
