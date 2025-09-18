// @ts-check

/** @module @web/fields/temporal/remaining_days/remaining_days_field - Deadline countdown field showing remaining days with color-coded urgency */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { getClassNameFromDecoration } from "@web/core/utils/decorations";
import { capitalize } from "@web/core/utils/format/strings";
import { formatDate } from "@web/fields/formatters";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { DateTimeField } from "@web/fields/temporal/datetime/datetime_field";

const { DateTime } = luxon;

export class RemainingDaysField extends Component {
    static components = { DateTimeField };

    static props = {
        ...standardFieldProps,
        classes: { type: Object, optional: true },
    };

    static defaultProps = {
        classes: {
            bf: "days <= 0",
            danger: "days < 0",
            warning: "days == 0",
        },
    };

    static template = "web.RemainingDaysField";

    /** @returns {number|null} Number of days until the deadline, or null if unset */
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

    /** @returns {string} Human-readable relative date string (e.g. "yesterday", "in 3 days") */
    get diffString() {
        if (this.diffDays === null) {
            return "";
        }
        if (Math.abs(this.diffDays) > 99) {
            return this.formattedValue;
        }
        const { record, name } = this.props;
        const value = record.data[name];
        return capitalize(value.toRelativeCalendar());
    }

    /** @returns {string} Locale-formatted date string */
    get formattedValue() {
        const { record, name } = this.props;
        return formatDate(record.data[name]);
    }

    /** @returns {string} Numeric-formatted date string */
    get numericValue() {
        const { record, name } = this.props;
        return formatDate(record.data[name], { numeric: true });
    }

    /** @returns {Object|null} Decoration class names evaluated against remaining days */
    get classNames() {
        if (this.diffDays === null) {
            return null;
        }
        if (!this.props.record.isActive) {
            return null;
        }
        const classNames = {};
        const evalContext = {
            days: this.diffDays,
            record: this.props.record.evalContext,
        };
        for (const decoration in this.props.classes) {
            const value = evaluateExpr(this.props.classes[decoration], evalContext);
            classNames[getClassNameFromDecoration(decoration)] = value;
        }
        return classNames;
    }

    /** @returns {Object} Props subset compatible with DateTimeField */
    get dateTimeFieldProps() {
        return Object.fromEntries(
            Object.entries(this.props).filter(([key]) => standardFieldProps[key]),
        );
    }
}

export const remainingDaysField = {
    component: RemainingDaysField,
    displayName: _t("Remaining Days"),
    supportedTypes: ["date", "datetime"],
    extractProps: ({ options }) => ({
        classes: options.classes,
    }),
};

registry.category("fields").add("remaining_days", remainingDaysField);
