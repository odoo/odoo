import { Component, proxy, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { formatDate, parseDate } from "@web/core/l10n/dates";
import { computePeriodRange } from "./period_utils";

const { DateTime } = luxon;

/**
 * Balance Sheet single-date filter, mirroring Enterprise account_reports.AccountReportFilterDate
 * (range_mode = false): Today, End of Month / Quarter / Fiscal Year, Specific Date.
 */
export class FsReportFilterDate extends Component {
    static template = "account_fs_report.FsReportFilterDate";
    static components = { DateTimeInput, Dropdown, DropdownItem };
    props = useProps({
        dateTo: t.any(),
        periodType: t.string(),
        fiscalStartDay: t.number().optional(1),
        fiscalStartMonth: t.number().optional(1),
        onPeriodSelected: t.function(),
    });

    setup() {
        this.state = proxy({
            editing: false,
            periods: this._buildPeriodState(this.props.dateTo, this.props.periodType),
        });
    }

    get filters() {
        return [
            { key: "today", label: _t("Today"), sequence: 0 },
            {
                key: "month",
                label: _t("End of Month"),
                months_per_period: 1,
                start_day: this.props.fiscalStartDay,
                start_month: this.props.fiscalStartMonth,
                sequence: 10,
            },
            {
                key: "quarter",
                label: _t("End of Quarter"),
                months_per_period: 3,
                start_day: this.props.fiscalStartDay,
                start_month: this.props.fiscalStartMonth,
                sequence: 20,
            },
            {
                key: "year",
                label: _t("End of Fiscal Year"),
                months_per_period: 12,
                start_day: this.props.fiscalStartDay,
                start_month: this.props.fiscalStartMonth,
                sequence: 30,
            },
        ];
    }

    get dateDescription() {
        return _t("As of %s", formatDate(this.props.dateTo));
    }

    get customDateTo() {
        return this.state.periods.custom[1];
    }

    isFilterDateSelected(periodType) {
        return this.props.periodType === periodType;
    }

    getPeriodDates(date, filter) {
        return computePeriodRange(
            date,
            filter.start_day,
            filter.start_month,
            filter.months_per_period
        );
    }

    getFilterDateDisplay(filter) {
        const [, dateTo] = this.state.periods[filter.key];
        const format = (d, fmt) => formatDate(d, fmt ? { format: fmt } : undefined);

        if (filter.key === "today") {
            return filter.label;
        }

        const isEndOfMonth = dateTo.ts === dateTo.endOf("month").startOf("day").ts;
        if (isEndOfMonth && filter.key === "month") {
            return format(dateTo, "MMMM yyyy");
        }
        if (filter.key === "quarter") {
            const dateFormat = isEndOfMonth ? "MMM yyyy" : undefined;
            const [dateFrom] = this.getPeriodDates(dateTo, filter);
            return `${format(dateFrom, dateFormat)} - ${format(dateTo, dateFormat)}`;
        }

        const isEndOfYear = dateTo.ts === dateTo.endOf("year").startOf("day").ts;
        if (isEndOfYear && filter.key === "year") {
            return format(dateTo, "yyyy");
        }
        // Fiscal year ending mid-year still shows the year of date_to.
        if (filter.key === "year") {
            return format(dateTo, "yyyy");
        }
        return format(dateTo);
    }

    selectDateFilter(periodType) {
        if (this.isFilterDateSelected(periodType)) {
            this.state.editing = periodType;
            return;
        }
        const [, dateTo] = this.state.periods[periodType];
        this._applyPeriod(periodType, dateTo);
    }

    selectNewPeriod(filter, side) {
        let [dateFrom, dateTo] = this.state.periods[filter.key];
        const direction = Math.sign(side);

        if (direction === -1) {
            [dateFrom, dateTo] = this.getPeriodDates(dateTo, filter);
        }

        const reference = direction === 1 ? dateTo : dateFrom;
        const newPeriodDate = reference.plus({ days: direction });
        const [, newDateTo] = computePeriodRange(
            newPeriodDate,
            filter.start_day,
            filter.start_month,
            filter.months_per_period
        );
        this._applyPeriod(filter.key, newDateTo);
    }

    writeDate(filter, inputElement) {
        const inputText = inputElement?.value;
        if (!inputText || this.state.editing !== filter.key) {
            return;
        }
        this.state.editing = false;
        try {
            const [, dateTo] = this.parseDateInput(filter, inputText);
            this._applyPeriod(filter.key, dateTo);
        } catch (error) {
            if (error.name !== "ConversionError") {
                throw error;
            }
        }
    }

    parseDateInput(filter, input) {
        const rawDateText = input.split("-").pop().trim();
        const tzOptions = { tz: "UTC" };
        let dateTo;
        const formats = ["LLL yyyy", "LLLL yyyy", "yyyy", undefined];
        let index = 0;
        while (!dateTo && index < formats.length) {
            try {
                dateTo = parseDate(rawDateText, { ...tzOptions, format: formats[index++] });
            } catch (error) {
                if (error.name !== "ConversionError" || index >= formats.length) {
                    throw error;
                }
            }
        }
        return computePeriodRange(
            dateTo,
            filter.start_day,
            filter.start_month,
            filter.months_per_period
        );
    }

    setCustomDateTo(dateTo) {
        if (!dateTo) {
            return;
        }
        const next = dateTo.startOf("day");
        this.state.periods.custom = [false, next];
        this._applyPeriod("custom", next);
    }

    _applyPeriod(periodType, dateTo) {
        const next =
            periodType === "today"
                ? DateTime.utc().startOf("day")
                : dateTo.startOf("day");
        this.state.editing = false;
        this.state.periods[periodType] = [false, next];
        if (periodType !== "custom") {
            this.state.periods.custom = [false, next];
        }
        this.props.onPeriodSelected({ periodType, dateTo: next });
    }

    _buildPeriodState(referenceDate, selectedPeriodType) {
        const today = DateTime.utc().startOf("day");
        const reference = referenceDate || today;
        const periods = {
            today: [false, today],
            custom: [false, reference],
        };
        for (const filter of this.filters) {
            if (filter.key === "today") {
                continue;
            }
            const filterReference =
                selectedPeriodType === filter.key
                    ? reference
                    : today;
            const [, dateTo] = computePeriodRange(
                filterReference,
                filter.start_day,
                filter.start_month,
                filter.months_per_period
            );
            periods[filter.key] = [false, dateTo];
        }
        return periods;
    }
}
