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

/**
 * Ordered thresholds `diffString` uses to pick the unit a date's relative distance is displayed
 * in: the first entry whose gap (measured in `thresholdUnit`) is at most `maxUnits` wins, and the
 * date is rendered one level more precisely, in `displayUnit`, instead of Luxon's default (which
 * can be ambiguous, e.g. "next month" for anywhere between 1 and 60 days).
 *
 * Example: a date 24 days away is within 1 month, so the "months" entry matches and it's shown in
 * weeks instead: "In 4 weeks". A date 3 years away matches nothing before the catch-all, so it
 * falls back to years: "In 3 years".
 *
 * `verifyCalendarBoundary` guards the "months" entry against variable month lengths: from Jan 30,
 * the diff to Mar 1 would floor to 1 month and wrongly match without it, even though Mar 1 is
 * really in the month *after* next.
 */
const RELATIVE_RANGES = [
    { thresholdUnit: "weeks", displayUnit: "days", maxUnits: 1 },
    { thresholdUnit: "months", displayUnit: "weeks", maxUnits: 1, verifyCalendarBoundary: true },
    { thresholdUnit: "years", displayUnit: "months", maxUnits: 1 },
    { thresholdUnit: "years", displayUnit: "years", maxUnits: Infinity },
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

        const unit = RELATIVE_RANGES.find(({ thresholdUnit, maxUnits, verifyCalendarBoundary }) => {
            const delta = Math.floor(Math.abs(v.diff(today, thresholdUnit)[thresholdUnit]));
            return (
                delta <= maxUnits &&
                (!verifyCalendarBoundary ||
                    (v >= today.minus({ [thresholdUnit]: maxUnits }).startOf(thresholdUnit) &&
                        v <= today.plus({ [thresholdUnit]: maxUnits }).endOf(thresholdUnit)))
            );
        }).displayUnit;

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
