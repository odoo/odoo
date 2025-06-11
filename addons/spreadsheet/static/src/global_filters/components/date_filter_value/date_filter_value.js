import { Component, onWillUpdateProps } from "@odoo/owl";
import {
    dateFilterValueToString,
    getDateRange,
    RELATIVE_PERIODS,
} from "@spreadsheet/global_filters/helpers";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
const { DateTime } = luxon;

const DATE_OPTIONS = [
    {
        id: "last_7_days",
        type: "relative",
        label: RELATIVE_PERIODS["last_7_days"],
    },
    {
        id: "last_30_days",
        type: "relative",
        label: RELATIVE_PERIODS["last_30_days"],
    },
    {
        id: "last_90_days",
        type: "relative",
        label: RELATIVE_PERIODS["last_90_days"],
        separator: true,
    },
    {
        id: "month",
        type: "month",
        label: _t("Month"),
    },
    {
        id: "quarter",
        type: "quarter",
        label: _t("Quarter"),
        separator: true,
    },
    {
        id: "year_to_date",
        type: "relative",
        label: RELATIVE_PERIODS["year_to_date"],
    },
    {
        id: "last_12_months",
        type: "relative",
        label: RELATIVE_PERIODS["last_12_months"],
    },
    {
        id: "year",
        type: "year",
        label: _t("Year"),
        separator: true,
    },
    {
        id: undefined,
        type: undefined,
        label: _t("All time"),
    },
    {
        id: "range",
        type: "range",
        label: _t("Custom Range"),
    },
];

/**
 * This component is used to select a date filter value.
 * It allows the user to select a month, quarter, year, or a custom date range.
 * It also provides options for relative periods like "last 7 days".
 */
export class DateFilterValue extends Component {
    static template = "spreadsheet.DateFilterValue";
    static components = { Dropdown, DropdownItem, DateTimeInput };
    static props = {
        value: { type: Object, optional: true },
        update: Function,
    };

    setup() {
        this._computeDefaultSelectedValues();
        this._applyCurrentValueToSelectedValues(this.props.value);
        onWillUpdateProps((nextProps) => this._applyCurrentValueToSelectedValues(nextProps.value));
    }

    /**
     * Computes the default selected values based on the current date.
     */
    _computeDefaultSelectedValues() {
        const now = DateTime.local();
        this.selectedValues = {
            month: { month: now.month, year: now.year },
            quarter: { quarter: Math.ceil(now.month / 3), year: now.year },
            year: { year: now.year },
            range: { from: "", to: "" },
        };
    }

    /**
     * Updates the default selected values based on the current value.
     * This method is called whenever the component's props are updated.
     */
    _applyCurrentValueToSelectedValues(value) {
        this._setRangeToCurrentValue(value);
        switch (value?.type) {
            case "month":
                this.selectedValues.month = {
                    month: value.month,
                    year: value.year,
                };
                break;
            case "quarter":
                this.selectedValues.quarter = {
                    quarter: value.quarter,
                    year: value.year,
                };
                break;
            case "year":
                this.selectedValues.year = { year: value.year };
                break;
            case "range":
                this.selectedValues.range = {
                    from: value.from,
                    to: value.to,
                };
                break;
        }
    }

    _setRangeToCurrentValue(value) {
        const { from, to } = getDateRange(value);
        const now = DateTime.local();
        this.selectedValues.range = {
            from: from ? from.toISODate() : now.startOf("month").toISODate(),
            to: to ? to.toISODate() : now.endOf("month").toISODate(),
        };
    }

    get inputValue() {
        return dateFilterValueToString(this.props.value);
    }

    get dateOptions() {
        return DATE_OPTIONS;
    }

    isMonthQuarterYear(value) {
        return ["month", "quarter", "year"].includes(value.type);
    }

    isSelected(value) {
        if (!this.props.value) {
            return value.id === undefined;
        }
        if (this.props.value.type === "relative") {
            return this.props.value.period === value.id;
        }
        return this.props.value.type === value.type;
    }

    update(value) {
        switch (value.type) {
            case "relative":
                this.props.update({ type: "relative", period: value.id });
                break;
            case "month":
                this.props.update({ type: "month", ...this.selectedValues.month });
                break;
            case "quarter":
                this.props.update({ type: "quarter", ...this.selectedValues.quarter });
                break;
            case "year":
                this.props.update({ type: "year", ...this.selectedValues.year });
                break;
            case "range":
                this.props.update({ type: "range", ...this.selectedValues.range });
                break;
            default:
                this.props.update(undefined);
        }
    }

    dateFrom() {
        return this.selectedValues.range.from
            ? DateTime.fromISO(this.selectedValues.range.from)
            : undefined;
    }

    dateTo() {
        return this.selectedValues.range.to
            ? DateTime.fromISO(this.selectedValues.range.to)
            : undefined;
    }

    setDateFrom(date) {
        this.selectedValues.range.from = date ? date.toISODate() : "";
        this.update({ type: "range" });
    }
    setDateTo(date) {
        this.selectedValues.range.to = date ? date.toISODate() : "";
        this.update({ type: "range" });
    }

    getDescription(type) {
        return dateFilterValueToString({ type, ...this.selectedValues[type] });
    }

    selectPrevious(type) {
        if (type === "month") {
            this._selectPreviousMonth();
        } else if (type === "quarter") {
            this._selectPreviousQuarter();
        } else if (type === "year") {
            this._selectPreviousYear();
        }
    }

    selectNext(type) {
        if (type === "month") {
            this._selectNextMonth();
        } else if (type === "quarter") {
            this._selectNextQuarter();
        } else if (type === "year") {
            this._selectNextYear();
        }
    }

    _selectPreviousQuarter() {
        const date = DateTime.local()
            .set({
                month: this.selectedValues.quarter.quarter * 3 - 2,
                year: this.selectedValues.quarter.year,
            })
            .minus({ months: 3 });
        this.selectedValues.quarter = {
            quarter: Math.ceil(date.month / 3),
            year: date.year,
        };
    }

    _selectNextQuarter() {
        const date = DateTime.local()
            .set({
                month: this.selectedValues.quarter.quarter * 3 - 2,
                year: this.selectedValues.quarter.year,
            })
            .plus({ months: 3 });
        this.selectedValues.quarter = {
            quarter: Math.ceil(date.month / 3),
            year: date.year,
        };
    }

    _selectPreviousMonth() {
        const date = DateTime.local()
            .set({
                month: this.selectedValues.month.month,
                year: this.selectedValues.month.year,
            })
            .minus({ months: 1 });
        this.selectedValues.month = {
            month: date.month,
            year: date.year,
        };
    }

    _selectNextMonth() {
        const date = DateTime.local()
            .set({
                month: this.selectedValues.month.month,
                year: this.selectedValues.month.year,
            })
            .plus({ months: 1 });
        this.selectedValues.month = {
            month: date.month,
            year: date.year,
        };
    }

    _selectPreviousYear() {
        this.selectedValues.year.year -= 1;
    }

    _selectNextYear() {
        this.selectedValues.year.year += 1;
    }
}
