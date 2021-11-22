/** @odoo-module **/

import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { registry } from "@web/core/registry";
import {
    formatDate,
    parseDate,
    parseDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class RemainingDaysField extends Component {
    get hasTime() {
        return this.props.type === "datetime";
    }

    get pickerComponent() {
        return this.hasTime ? DateTimePicker : DatePicker;
    }

    get parsedValue() {
        const parser = this.hasTime ? parseDateTime : parseDate;
        return this.props.value ? parser(this.props.value, { timezone: false }) : undefined;
    }

    get diffDays() {
        if (!this.props.value) {
            return null;
        }
        const today = luxon.DateTime.local().startOf("day");
        return Math.floor(this.parsedValue.startOf("day").diff(today, "days").days);
    }

    get formattedValue() {
        return this.props.value ? formatDate(this.parsedValue, { timezone: true }) : "";
    }

    /**
     * @param {CustomEvent} ev
     */
    onChange(ev) {
        const serializer = this.hasTime ? serializeDateTime : serializeDate;
        this.props.update(serializer(ev.detail.date));
    }
}

Object.assign(RemainingDaysField, {
    template: "web.RemainingDaysField",
    props: {
        ...standardFieldProps,
    },
});

registry.category("fields").add("remaining_days", RemainingDaysField);
