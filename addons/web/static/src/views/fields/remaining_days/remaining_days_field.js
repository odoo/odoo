/** @odoo-module **/

import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class RemainingDaysField extends Component {
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
            this.props.update(datetime);
        } else if (typeof datetime === "string") {
            // when the date is cleared
            this.props.update(false);
        }
    }
}

RemainingDaysField.template = "web.RemainingDaysField";
RemainingDaysField.props = {
    ...standardFieldProps,
};

RemainingDaysField.displayName = _lt("Remaining Days");
RemainingDaysField.supportedTypes = ["date", "datetime"];

registry.category("fields").add("remaining_days", RemainingDaysField);
