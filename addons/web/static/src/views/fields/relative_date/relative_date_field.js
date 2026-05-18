import { Component } from "@odoo/owl";
import { evaluateExpr } from "@web/core/py_js/py";
import { getClassNameFromDecoration } from "@web/views/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { DateTimeField } from "../datetime/datetime_field";
import { standardFieldProps } from "../standard_field_props";
import { capitalize } from "@web/core/utils/strings";
import { formatDate } from "../formatters";

const { DateTime } = luxon;

export class RelativeDateField extends Component {
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

    static template = "web.RelativeDateField";

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

    get diffString() {
        const diffDays = this.diffDays;
        if (diffDays === null) {
            return "";
        }
        if (Math.abs(diffDays) > 99) {
            return this.formattedValue;
        }
        const { record, name } = this.props;
        const value = record.data[name];
        const relativeCalendarOptions = {};
        if (Math.abs(diffDays) <= 30) {
            relativeCalendarOptions.unit = "days";
        }
        return capitalize(value.toRelativeCalendar(relativeCalendarOptions));
    }

    get formattedValue() {
        const { record, name } = this.props;
        return formatDate(record.data[name]);
    }

    get numericValue() {
        const { record, name } = this.props;
        return formatDate(record.data[name], { numeric: true });
    }

    get classNames() {
        if (this.diffDays === null) {
            return null;
        }
        if (!this.props.record.isActive) {
            return null;
        }
        const classNames = {};
        const evalContext = { days: this.diffDays, record: this.props.record.evalContext };
        for (const decoration in this.props.classes) {
            const value = evaluateExpr(this.props.classes[decoration], evalContext);
            classNames[getClassNameFromDecoration(decoration)] = value;
        }
        return classNames;
    }

    get dateTimeFieldProps() {
        return Object.fromEntries(
            Object.entries(this.props).filter(([key]) => standardFieldProps[key])
        );
    }
}

export const relativeDateField = {
    component: RelativeDateField,
    displayName: _t("Remaining Days"),
    supportedTypes: ["date", "datetime"],
    extractProps: ({ options }) => ({
        classes: options.classes,
    }),
};

registry.category("fields").add("relative_date", relativeDateField);
