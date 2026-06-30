import { Component, props, t } from "@odoo/owl";
import { evaluateExpr } from "@web/core/py_js/py";
import { getClassNameFromDecoration } from "@web/views/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { DateTimeField } from "../datetime/datetime_field";
import { standardFieldProps } from "../standard_field_props";
import { capitalize } from "@web/core/utils/strings";
import { formatDate } from "../formatters";

const { DateTime } = luxon;

const CONFIGURED_UNITS = [
    { unit: "weeks",  target: "days",   quantity: 1 },
    { unit: "months", target: "weeks",  quantity: 1, checkOverlap: true },
    { unit: "years",  target: "months", quantity: 1 },
];

export class RelativeDateField extends Component {
    static components = { DateTimeField };

    props = props({
        ...standardFieldProps,
        classes: t.object().optional({
            bf: "days <= 0",
            danger: "days < 0",
            warning: "days == 0",
        }),
    });

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
        if (this.diffDays === null) {
            return "";
        }
        const { record, name } = this.props;
        const value = record.data[name];
        const today = DateTime.local().startOf("day");
        const v = value.startOf("day");

        let unit = "years";
        for (const { unit: checkUnit, target, quantity, checkOverlap } of CONFIGURED_UNITS) {
            const delta = Math.floor(Math.abs(v.diff(today, checkUnit)[checkUnit]));
            if (delta <= quantity && (!checkOverlap || (
                v >= today.minus({ [checkUnit]: quantity }).startOf(checkUnit) &&
                v <= today.plus({ [checkUnit]: quantity }).endOf(checkUnit)
            ))) {
                unit = target;
                break;
            }
        }

        return capitalize(value.toRelativeCalendar({ unit }));
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
