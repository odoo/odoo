import { Component, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { RecordSelector } from "@web/core/record_selectors/record_selector";
import { formatDate } from "@web/core/l10n/dates";

/**
 * Mirrors Enterprise AccountReportFilterComparison (single + range modes).
 */
export class FsReportFilterComparison extends Component {
    static template = "account_fs_report.FsReportFilterComparison";
    static components = { DateTimeInput, Dropdown, DropdownItem, RecordSelector };
    props = useProps({
        compare: t.string(),
        numberPeriod: t.number(),
        periodOrder: t.string(),
        growthDisplay: t.string(),
        customDate: t.any(),
        customDateFrom: t.any().optional(),
        asOf: t.any(),
        dateFrom: t.any().optional(),
        rangeMode: t.boolean().optional(false),
        baseReportLineId: t.any().optional(),
        reportId: t.number(),
        onComparisonChange: t.function(),
    });

    get isRangeMode() {
        return Boolean(this.props.rangeMode);
    }

    get availablePeriodOrder() {
        return { descending: _t("Descending"), ascending: _t("Ascending") };
    }

    get periodLabel() {
        return this.props.numberPeriod > 1 ? _t("Periods") : _t("Period");
    }

    get buttonSuffix() {
        if (this.props.compare === "previous_period") {
            if (this.props.numberPeriod === 1) {
                return _t("Previous Period");
            }
            return _t("%s Previous Periods", this.props.numberPeriod);
        }
        if (this.props.compare === "same_last_year") {
            if (this.props.numberPeriod === 1) {
                return _t("Previous Year");
            }
            return _t("%s Previous Years", this.props.numberPeriod);
        }
        if (this.props.compare === "custom") {
            if (this.isRangeMode && this.props.customDateFrom) {
                return _t("%(date_from)s - %(date_to)s", {
                    date_from: formatDate(this.props.customDateFrom),
                    date_to: formatDate(this.props.customDate),
                });
            }
            return formatDate(this.props.customDate);
        }
        if (this.props.compare === "report_line" && this.props.baseReportLineId) {
            return null;
        }
        return "";
    }

    get reportLineComparisonProps() {
        // Enterprise: domain expression_ids != False (any line with a balance expression),
        // including section totals. Community mirrors that: formula lines OR parents that
        // roll up children (formula_type=none section headers like Current Assets).
        return {
            resModel: "fs.report.line",
            domain: [
                ["report_id", "=", this.props.reportId],
                "|",
                ["formula_type", "!=", "none"],
                ["child_ids", "!=", false],
            ],
            resId: this.props.baseReportLineId || false,
            update: (resId) => this.onBaseReportLineSelected(resId),
            fieldString: _t("Report Lines"),
        };
    }

    selectFilter(filter) {
        // Enterprise defaults custom comparison dates to the current period.
        if (filter === "custom") {
            const patch = {
                compare: "custom",
                customDate: this.props.asOf || this.props.customDate,
            };
            if (this.isRangeMode) {
                patch.customDateFrom = this.props.dateFrom || this.props.customDateFrom || this.props.asOf;
            }
            this.props.onComparisonChange(patch);
            return;
        }
        this.props.onComparisonChange({ compare: filter });
    }

    setNumberPeriods(ev) {
        const numberPeriod = parseInt(ev.target.value, 10);
        if (numberPeriod >= 1) {
            this.props.onComparisonChange({ numberPeriod });
        }
    }

    setCustomDate(dateTo) {
        if (!dateTo) {
            return;
        }
        this.props.onComparisonChange({
            compare: "custom",
            customDate: dateTo.startOf("day"),
        });
    }

    setCustomDateFrom(dateFrom) {
        if (!dateFrom) {
            return;
        }
        const nextFrom = dateFrom.startOf("day");
        let nextTo = this.props.customDate;
        if (!nextTo || nextTo < nextFrom) {
            nextTo = nextFrom;
        }
        this.props.onComparisonChange({
            compare: "custom",
            customDateFrom: nextFrom,
            customDate: nextTo,
        });
    }

    setPeriodOrder(ev) {
        this.props.onComparisonChange({ periodOrder: ev.target.value });
    }

    setGrowthDisplay(ev) {
        this.props.onComparisonChange({ growthDisplay: ev.target.value });
    }

    onBaseReportLineSelected(resId) {
        if (!resId) {
            this.props.onComparisonChange({
                compare: "no_comparison",
                baseReportLineId: false,
            });
            return;
        }
        this.props.onComparisonChange({
            compare: "report_line",
            baseReportLineId: resId,
        });
    }
}
