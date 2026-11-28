import { Component, proxy, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { formatDate, parseDate } from "@web/core/l10n/dates";
import { buildRangeDateLabel, computePeriodRange } from "./period_utils";

const { DateTime } = luxon;

/**
 * Enterprise AccountReportFilterDate — single (BS) and range (P&L) modes.
 */
export class FsReportFilterDate extends Component {
    static template = "account_fs_report.FsReportFilterDate";
    static components = { DateTimeInput, Dropdown, DropdownItem };
    props = useProps({
        dateFrom: t.any().optional(),
        dateTo: t.any(),
        periodType: t.string(),
        rangeMode: t.boolean().optional(false),
        fiscalStartDay: t.number().optional(1),
        fiscalStartMonth: t.number().optional(1),
        onPeriodSelected: t.function(),
    });

    setup() {
        this.state = proxy({
            editing: false,
            periods: this._buildPeriodState(
                this.props.dateFrom,
                this.props.dateTo,
                this.props.periodType
            ),
        });
    }

    get isRangeMode() {
        return Boolean(this.props.rangeMode);
    }

    get filters() {
        const startDay = this.props.fiscalStartDay;
        const startMonth = this.props.fiscalStartMonth;
        const filters = [];
        if (!this.isRangeMode) {
            filters.push({ key: "today", label: _t("Today"), sequence: 0 });
        }
        filters.push(
            {
                key: "month",
                label: this.isRangeMode ? _t("Month") : _t("End of Month"),
                months_per_period: 1,
                start_day: startDay,
                start_month: startMonth,
                sequence: 10,
            },
            {
                key: "quarter",
                label: this.isRangeMode ? _t("Quarter") : _t("End of Quarter"),
                months_per_period: 3,
                start_day: startDay,
                start_month: startMonth,
                sequence: 20,
            },
            {
                key: "year",
                label: this.isRangeMode ? _t("Fiscal Year") : _t("End of Fiscal Year"),
                months_per_period: 12,
                start_day: startDay,
                start_month: startMonth,
                sequence: 30,
            }
        );
        return filters;
    }

    get dateDescription() {
        if (!this.isRangeMode) {
            return _t("As of %s", formatDate(this.props.dateTo));
        }
        return buildRangeDateLabel(
            this.props.dateFrom,
            this.props.dateTo,
            this.props.periodType,
            this.props.fiscalStartDay,
            this.props.fiscalStartMonth
        );
    }

    get customDateFrom() {
        return this.state.periods.custom[0];
    }

    get customDateTo() {
        return this.state.periods.custom[1];
    }

    get dateModeAttr() {
        return this.isRangeMode ? "range" : "single";
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
        const [dateFrom, dateTo] = this.state.periods[filter.key];
        const format = (d, fmt) => formatDate(d, fmt ? { format: fmt } : undefined);

        if (filter.key === "today") {
            return filter.label;
        }

        if (this.isRangeMode) {
            if (filter.key === "month") {
                const isEndOfMonth = dateTo.ts === dateTo.endOf("month").startOf("day").ts;
                if (isEndOfMonth) {
                    return format(dateTo, "MMMM yyyy");
                }
            }
            if (filter.key === "quarter") {
                const isEndOfMonth = dateTo.ts === dateTo.endOf("month").startOf("day").ts;
                const dateFormat = isEndOfMonth ? "MMM yyyy" : undefined;
                return `${format(dateFrom, dateFormat)} - ${format(dateTo, dateFormat)}`;
            }
            if (filter.key === "year") {
                return format(dateTo, "yyyy");
            }
            return `${format(dateFrom)} - ${format(dateTo)}`;
        }

        const isEndOfMonth = dateTo.ts === dateTo.endOf("month").startOf("day").ts;
        if (isEndOfMonth && filter.key === "month") {
            return format(dateTo, "MMMM yyyy");
        }
        if (filter.key === "quarter") {
            const dateFormat = isEndOfMonth ? "MMM yyyy" : undefined;
            const [from] = this.getPeriodDates(dateTo, filter);
            return `${format(from, dateFormat)} - ${format(dateTo, dateFormat)}`;
        }
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
        const [dateFrom, dateTo] = this.state.periods[periodType];
        this._applyPeriod(periodType, dateFrom, dateTo);
    }

    selectNewPeriod(filter, side) {
        let [dateFrom, dateTo] = this.state.periods[filter.key];
        const direction = Math.sign(side);

        if (!this.isRangeMode && direction === -1) {
            [dateFrom, dateTo] = this.getPeriodDates(dateTo, filter);
        }

        const reference = direction === 1 ? dateTo : dateFrom;
        const newPeriodDate = reference.plus({ days: direction });
        const [newFrom, newTo] = computePeriodRange(
            newPeriodDate,
            filter.start_day,
            filter.start_month,
            filter.months_per_period
        );
        this._applyPeriod(filter.key, newFrom, newTo);
    }

    writeDate(filter, inputElement) {
        const inputText = inputElement?.value;
        if (!inputText || this.state.editing !== filter.key) {
            return;
        }
        this.state.editing = false;
        try {
            const [dateFrom, dateTo] = this.parseDateInput(filter, inputText);
            this._applyPeriod(filter.key, dateFrom, dateTo);
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

    setCustomDateFrom(dateFrom) {
        if (!dateFrom) {
            return;
        }
        const nextFrom = dateFrom.startOf("day");
        let nextTo = this.state.periods.custom[1];
        if (!nextTo || nextTo < nextFrom) {
            nextTo = nextFrom;
        }
        this.state.periods.custom = [nextFrom, nextTo];
        this._applyPeriod("custom", nextFrom, nextTo);
    }

    setCustomDateTo(dateTo) {
        if (!dateTo) {
            return;
        }
        const nextTo = dateTo.startOf("day");
        let nextFrom = this.state.periods.custom[0];
        if (this.isRangeMode) {
            if (!nextFrom || nextFrom > nextTo) {
                nextFrom = nextTo;
            }
            this.state.periods.custom = [nextFrom, nextTo];
            this._applyPeriod("custom", nextFrom, nextTo);
            return;
        }
        this.state.periods.custom = [false, nextTo];
        this._applyPeriod("custom", false, nextTo);
    }

    _applyPeriod(periodType, dateFrom, dateTo) {
        let nextTo = dateTo;
        let nextFrom = dateFrom;
        if (periodType === "today") {
            nextTo = DateTime.utc().startOf("day");
            nextFrom = false;
        } else {
            nextTo = dateTo.startOf("day");
            nextFrom = dateFrom && dateFrom.startOf ? dateFrom.startOf("day") : dateFrom;
        }
        if (this.isRangeMode && periodType !== "custom" && periodType !== "today") {
            const filter = this.filters.find((item) => item.key === periodType);
            [nextFrom, nextTo] = this.getPeriodDates(nextTo, filter);
        }
        this.state.editing = false;
        this.state.periods[periodType] = [nextFrom || false, nextTo];
        if (periodType !== "custom") {
            this.state.periods.custom = [nextFrom || false, nextTo];
        }
        this.props.onPeriodSelected({
            periodType,
            dateFrom: nextFrom || false,
            dateTo: nextTo,
        });
    }

    _buildPeriodState(referenceFrom, referenceTo, selectedPeriodType) {
        const today = DateTime.utc().startOf("day");
        const reference = referenceTo || today;
        const periods = {
            today: [false, today],
            custom: [
                this.isRangeMode ? referenceFrom || reference : false,
                reference,
            ],
        };
        for (const filter of this.filters) {
            if (filter.key === "today") {
                continue;
            }
            const filterReference =
                selectedPeriodType === filter.key ? reference : today;
            const [dateFrom, dateTo] = computePeriodRange(
                filterReference,
                filter.start_day,
                filter.start_month,
                filter.months_per_period
            );
            periods[filter.key] = [dateFrom, dateTo];
        }
        return periods;
    }
}
