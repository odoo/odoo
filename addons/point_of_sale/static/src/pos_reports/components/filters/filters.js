import { Component, proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { RecordSelector } from "@web/core/record_selectors/record_selector";
import { usePosReport } from "../../pos_report_plugin";

const { DateTime } = luxon;

export class PosReportFilters extends Component {
    static template = "pos_reports.PosReportFilters";
    static components = {
        DateTimeInput,
        Dropdown,
        DropdownItem,
        MultiRecordSelector,
        RecordSelector,
    };

    setup() {
        this.report = usePosReport();
        this.filters = this.report.meta()?.filters || [];

        const options = this.report.options() || {};
        const currentDate = options.date_from
            ? DateTime.fromSQL(options.date_from)
            : DateTime.now();

        const dateFilter = this.filters.find((f) => f.type === "date_range");

        this.state = proxy({
            selectedDateFilter: (dateFilter && dateFilter.default) || "month",
            currentDate,
            customDateFrom: DateTime.now().startOf("month"),
            customDateTo: DateTime.now().endOf("month"),
        });
    }

    get dateFilter() {
        return this.filters.find((f) => f.type === "date_range");
    }

    get multiSelectFilters() {
        return this.filters.filter((f) => f.type === "multi_select");
    }

    get singleSelectFilters() {
        return this.filters.filter((f) => f.type === "single_select");
    }

    get extraOptions() {
        const options = this.report.options();
        return [
            {
                name: _t("Unfold All"),
                active: !!options.unfold_all,
                onSelect: () => this.report.unfoldAll(),
            },
            ...this.filters
                .filter(({ type }) => type === "extra_option")
                .map(({ key, label }) => ({
                    name: label,
                    active: !!options[key],
                    onSelect: () => this.report.applyFilters({ [key]: !options[key] }),
                })),
        ];
    }

    get availableDateFilters() {
        return [
            { key: "month", label: _t("Month") },
            { key: "year", label: _t("Year") },
        ];
    }

    getDateRange(type) {
        const baseDate = this.state.currentDate;
        switch (type) {
            case "month":
                return {
                    from: baseDate.startOf("month"),
                    to: baseDate.endOf("month"),
                };
            case "year":
                return {
                    from: baseDate.startOf("year"),
                    to: baseDate.endOf("year"),
                };
            default:
                return {
                    from: baseDate.startOf("month"),
                    to: baseDate.endOf("month"),
                };
        }
    }

    getDateDescription() {
        const dt = this.state.currentDate;
        switch (this.state.selectedDateFilter) {
            case "month":
                return dt.toFormat("MMM yyyy");
            case "year":
                return dt.toFormat("yyyy");
            case "custom":
                return `${this.state.customDateFrom.toFormat(
                    "dd MMM yyyy"
                )} - ${this.state.customDateTo.toFormat("dd MMM yyyy")}`;
            default:
                return dt.toFormat("dd MMM yyyy");
        }
    }

    getFilterDateDisplay(filter) {
        const dt = this.state.currentDate;
        switch (filter.key) {
            case "month":
                return dt.toFormat("MMM yyyy");
            case "year":
                return dt.toFormat("yyyy");
            default:
                return dt.toFormat("dd MMM yyyy");
        }
    }

    async selectDateFilter(key) {
        this.state.selectedDateFilter = key;
        this.state.currentDate = DateTime.now();

        const { from, to } = this.getDateRange(key);

        await this.report.applyFilters({
            date_from: from.toFormat("yyyy-MM-dd HH:mm:ss"),
            date_to: to.toFormat("yyyy-MM-dd HH:mm:ss"),
        });
    }

    async selectNewPeriod(filter, direction) {
        const amountMap = {
            month: { months: direction },
            year: { years: direction },
        };

        this.state.currentDate = this.state.currentDate.plus(amountMap[filter.key]);
        this.state.selectedDateFilter = filter.key;

        const { from, to } = this.getDateRange(filter.key);

        await this.report.applyFilters({
            date_from: from.toFormat("yyyy-MM-dd HH:mm:ss"),
            date_to: to.toFormat("yyyy-MM-dd HH:mm:ss"),
        });
    }

    setCustomDateFrom(dateFrom) {
        this.state.customDateFrom = dateFrom;
        this.applyCustomDates();
    }

    setCustomDateTo(dateTo) {
        this.state.customDateTo = dateTo;
        this.applyCustomDates();
    }

    async applyCustomDates() {
        const { customDateFrom, customDateTo } = this.state;

        if (!customDateFrom || !customDateTo) {
            return;
        }

        this.state.selectedDateFilter = "custom";
        await this.report.applyFilters({
            date_from: customDateFrom.toFormat("yyyy-MM-dd HH:mm:ss"),
            date_to: customDateTo.toFormat("yyyy-MM-dd HH:mm:ss"),
        });
    }

    getMultiRecordSelectorProps(filter) {
        return {
            resModel: filter.model,
            resIds: this.report.options()[filter.key] || [],
            placeholder: _t("All"),
            update: async (ids) => {
                await this.report.applyFilters({
                    [filter.key]: ids,
                });
            },
        };
    }

    getRecordSelectorProps(filter) {
        const value = this.report.options()[filter.key];
        return {
            resModel: filter.model,
            resId: value || false,
            placeholder: _t("All"),
            update: async (id) => {
                await this.report.applyFilters({
                    [filter.key]: id || false,
                });
            },
        };
    }
}
