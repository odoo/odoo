/** @odoo-module **/

import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _lt, _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";
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

    get diffString() {
        if (this.diffDays === null) {
            return "";
        }
        switch (this.diffDays) {
            case -1:
                return _t("Yesterday");
            case 0:
                return _t("Today");
            case 1:
                return _t("Tomorrow");
        }
        if (Math.abs(this.diffDays) > 99) {
            return this.formattedValue;
        }
        if (this.diffDays < 0) {
            return sprintf(_t("%s days ago"), -this.diffDays);
        }
        return sprintf(_t("In %s days"), this.diffDays);
    }

    get formattedValue() {
        return this.hasTime
            ? formatDateTime(this.props.value, { format: localization.dateFormat })
            : formatDate(this.props.value);
    }

    onDateTimeChanged(datetime) {
        this.props.update(datetime || false);
    }
}

RemainingDaysField.template = "web.RemainingDaysField";
RemainingDaysField.props = {
    ...standardFieldProps,
};

RemainingDaysField.displayName = _lt("Remaining Days");
RemainingDaysField.supportedTypes = ["date", "datetime"];

registry.category("fields").add("remaining_days", RemainingDaysField);
