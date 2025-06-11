import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { Expression } from "@web/core/tree_editor/condition_tree";
import { Select } from "@web/core/tree_editor/tree_editor_components";

const { DateTime } = luxon;

function range(start, stop) {
    const range = [];
    for (let i = start; i <= stop; i++) {
        range.push(i);
    }
    return range;
}

function isIntegerInRange(start, stop) {
    return (num) => Number.isInteger(num) && start <= num && num <= stop;
}

function getCurrent(unit) {
    return () => DateTime.now()[unit];
}

const CURRENT_MONTH = `context_today().month`;
const CURRENT_DAY = `context_today().day`;

export const OPTIONS_WITH_SELECT = new Set([
    "month_number",
    "day_of_month",
    "quarter_number",
    "day_of_week",
]);

export function getOptionsFor(name, allowExpressions = false) {
    switch (name) {
        case "month_number":
            return [
                ...(allowExpressions ? [[CURRENT_MONTH, _t("This month")]] : []),
                ...range(1, 12).map((month) => [
                    month,
                    luxon.DateTime.now().set({ month }).toFormat("MMMM"),
                ]),
            ];
        case "day_of_month":
            return [
                ...(allowExpressions ? [[CURRENT_DAY, _t("This day")]] : []),

                ...range(1, 31).map((day) => [
                    day,
                    luxon.DateTime.now().set({ day }).toFormat("d"),
                ]),
            ];
        case "quarter_number":
            return range(1, 4).map((quarter) => [quarter, _t("Quarter %(quarter)s", { quarter })]);
        case "day_of_week": {
            const { weekStart } = localization;
            return range(0, 6).map((weekday) => [
                (weekday + weekStart) % 7,
                luxon.DateTime.now()
                    .set({ weekday: (weekday + weekStart) % 7 })
                    .toFormat("cccc"),
            ]);
        }
    }
}

const UNITS = {
    month_number: "month",
    day_of_month: "day",
    quarter_number: "quarter",
    day_of_week: "weekday",
};

function toSelectValue(v) {
    return v instanceof Expression ? v._expr : v;
}

function fromSelectValue(v) {
    return typeof v === "string" ? new Expression(v) : v;
}

export function getEditorInfoForOptionsWithSelect(name, params) {
    const options = getOptionsFor(name, params.allowExpressions);
    const getOption = (value) => options.find(([v]) => v === toSelectValue(value)) || null;
    return {
        component: Select,
        extractProps: ({ value, update, displayPlaceholder }) => ({
            value: toSelectValue(value),
            update: (value) => update(fromSelectValue(value)),
            options,
            addBlankOption: params.addBlankOption,
            placeholder: displayPlaceholder && _t(`Select one or several criteria`),
        }),
        defaultValue: getCurrent(UNITS[name]),
        isSupported: (value) => typeof value !== "string" && getOption(value),
        message: _t("Value not in selection"),
    };
}

export const OPTIONS_WITH_INPUT = {
    year_number: {
        defaultValue: getCurrent("year"),
        isSupported: Number.isInteger,
    },
    day_of_year: {
        defaultValue: getCurrent("ordinal"),
        isSupported: isIntegerInRange(1, 366),
    },
    iso_week_number: {
        defaultValue: getCurrent("weekNumber"),
        isSupported: isIntegerInRange(1, 53),
    },
    hour_number: {
        defaultValue: getCurrent("hour"),
        isSupported: isIntegerInRange(0, 23),
    },
    minute_number: {
        defaultValue: getCurrent("minute"),
        isSupported: isIntegerInRange(0, 59),
    },
    second_number: {
        defaultValue: getCurrent("second"),
        isSupported: isIntegerInRange(0, 59),
    },
};
