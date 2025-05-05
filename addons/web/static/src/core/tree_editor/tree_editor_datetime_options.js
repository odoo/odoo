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

let day_of_week_options;
export const OPTIONS = {
    month_number: [
        [CURRENT_MONTH, _t("This month")],
        ...range(1, 12).map((month) => [
            month,
            luxon.DateTime.now().set({ month }).toFormat("MMMM"),
        ]),
    ],
    day_of_month: [
        [CURRENT_DAY, _t("This day")],
        ...range(1, 31).map((day) => [day, luxon.DateTime.now().set({ day }).toFormat("d")]),
    ],
    quarter_number: range(1, 4).map((quarter) => [quarter, _t("Quarter %(quarter)s", { quarter })]),
    get day_of_week() {
        if (!day_of_week_options) {
            const { weekStart } = localization; // we have to wait weekStart to be defined!
            day_of_week_options = range(0, 6).map((weekday) => [
                (weekday + weekStart) % 7,
                luxon.DateTime.now()
                    .set({ weekday: (weekday + weekStart) % 7 })
                    .toFormat("cccc"),
            ]);
        }
        return day_of_week_options;
    },
};

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

function makePartialValueEditorInfo(name) {
    const options = OPTIONS[name];
    return {
        component: Select,
        extractProps: ({ value, update }) => ({
            value: toSelectValue(value),
            update: (value) => update(fromSelectValue(value)),
            options,
        }),
        defaultValue: getCurrent(UNITS[name]),
        isSupported: (value) =>
            typeof value !== "string" && options.find(([v]) => v === toSelectValue(value)),
        message: _t("Value not in selection"),
    };
}

let day_of_week_editor_info;
export const OPTIONS_WITH_SELECT = {
    month_number: makePartialValueEditorInfo("month_number"),
    day_of_month: makePartialValueEditorInfo("day_of_month"),
    quarter_number: makePartialValueEditorInfo("quarter_number"),
    get day_of_week() {
        if (!day_of_week_editor_info) {
            day_of_week_editor_info = makePartialValueEditorInfo("day_of_week");
        }
        return day_of_week_editor_info;
    },
};

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
