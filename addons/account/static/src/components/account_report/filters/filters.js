/** @odoo-module native */
import { Component, status, useState } from "@odoo/owl";
import { DateTimeInput } from "@web/components/datetime";
import { Dropdown, DropdownItem } from "@web/components/dropdown";
import { WarningDialog } from "@web/components/errors";
import { MultiRecordSelector } from "@web/components/record_selectors";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { formatDate, parseDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";

import { DateTime } from "luxon";
function findNearestDropdownItem(navigator) {
    for (let i = navigator.activeItemIndex; i >= 0; i--) {
        if (navigator.items[i].target.classList.contains("o-dropdown-item")) {
            return navigator.items[i];
        }
    }
}

const log = makeLogger("account.report.filters");

export class AccountReportFilters extends Component {
    static template = "account.AccountReportFilters";
    static props = {};
    static components = {
        DateTimeInput,
        Dropdown,
        DropdownItem,
        MultiRecordSelector,
    };

    setup() {
        useLifecycleLog(log);
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.controller = useState(this.env.controller);
        if (this.env.controller.cachedFilterOptions.date) {
            this.dateFilter = useState(this.initDateFilters());
        }
        this.timeout = null;
    }

    focusInnerInput(selectedItem) {
        selectedItem.el.querySelector(":scope input")?.focus();
    }

    get filterExtraOptionsData() {
        return {
            unfold_all: {
                name: _t("Unfold All"),
                show: this.controller.filters.show_all,
            },
            integer_rounding_enabled: {
                name: _t("Integer Rounding"),
            },
            hide_0_lines: {
                name: _t("Hide lines at 0"),
                ui_filter: true,
                onSelect: () => this.toggleHideZeroLines(),
                show: this.controller.filters.show_hide_0_lines !== "never",
            },
            horizontal_split: {
                name: _t("Split Horizontally"),
                ui_filter: true,
                onSelect: () => this.toggleHorizontalSplit(),
            },
        };
    }

    get selectedVariantName() {
        for (const variant of this.controller.cachedFilterOptions.available_variants) {
            if (
                variant.id === this.controller.cachedFilterOptions.selected_variant_id
            ) {
                return variant.name;
            }
        }
        return _t("None");
    }

    get availablePeriodOrder() {
        return { descending: _t("Descending"), ascending: _t("Ascending") };
    }

    get periodOrder() {
        return this.controller.cachedFilterOptions.comparison.period_order ===
            "descending"
            ? _t("Descending")
            : _t("Ascending");
    }

    get selectedExtraOptions() {
        return "";
    }

    get periodHandlers() {
        return {
            month: {
                parse: (input) => this._parseMonthOffset(input),
                display: (dateTo) => this._displayMonth(dateTo),
            },
            quarter: {
                parse: (input) => this._parseQuarterOffset(input),
                display: (dateTo) => this._displayQuarter(dateTo),
            },
            year: {
                parse: (input) => this._parseYearOffset(input),
                display: (dateTo) => this._displayYear(dateTo),
            },
        };
    }

    get dropdownProps() {
        return {
            shouldFocusChildInput: false,
            hotkeys: {
                arrowright: (navigator) => this.focusInnerInput(navigator.activeItem),
            },
        };
    }

    get dateNavigationOptions() {
        return {
            hotkeys: {
                arrowleft: (navigator) => this._stepPeriodUnderNavigator(navigator, -1),
                arrowright: (navigator) => this._stepPeriodUnderNavigator(navigator, 1),
                enter: {
                    callback: (navigator) =>
                        this._selectPeriodUnderNavigator(navigator),
                    bypassEditableProtection: true,
                },
            },
            shouldFocusChildInput: false,
        };
    }

    _stepPeriodUnderNavigator(navigator, direction) {
        if (!navigator.activeItem) {
            return;
        }
        const periodType =
            findNearestDropdownItem(navigator)?.target.dataset.periodType;
        if (!Object.prototype.hasOwnProperty.call(this.dateFilter, periodType)) {
            return;
        }
        if (direction < 0) {
            this.selectPreviousPeriod(periodType);
        } else {
            this.selectNextPeriod(periodType);
        }
    }

    _selectPeriodUnderNavigator(navigator) {
        if (!navigator.activeItem) {
            return;
        }

        // While editing a date field, hovering another dropdown item makes the hovered one
        // active instead of the edited one. If the focused element is an input, reselect
        // its encompassing dropdown item.
        const focusedElement = document.activeElement;
        if (focusedElement.nodeName === "INPUT") {
            for (const navigatorItem of navigator.items) {
                if (navigatorItem.target.contains(focusedElement)) {
                    navigatorItem.setActive();
                    break;
                }
            }
        }

        const dropdownItem = findNearestDropdownItem(navigator);
        const isSelected = dropdownItem?.target.classList.contains("selected");
        const periodType = dropdownItem?.target.dataset.periodType;
        const mode = dropdownItem?.target.dataset.mode;
        const inputField =
            navigator.activeItem.target.nodeName === "INPUT"
                ? navigator.activeItem.target
                : dropdownItem?.target.querySelector("input.o_input");
        if (mode === "view" && periodType) {
            dropdownItem?.setActive();
            if (!isSelected) {
                // Select the period type on first enter.
                this.dateFilter.editing = false;
                this.filterClicked({
                    optionKey: "date.filter",
                    optionValue: periodType,
                    reload: true,
                });
            } else {
                // Make the input editable on second enter.
                this.editDateFilter(periodType, inputField);
            }
        } else if (mode === "edit" && periodType) {
            // Save the edited period and return focus to the dropdown item.
            this.saveDateFilter(periodType, inputField);
            dropdownItem?.setActive();
        } else if (periodType) {
            // Select the period type and potentially blur an input date field to trigger a save.
            inputField?.blur();
            this.selectDateFilter(periodType, true);
            dropdownItem?.setActive();
        }
    }

    get periodLabel() {
        return this.controller.cachedFilterOptions.comparison.number_period > 1
            ? _t("Periods")
            : _t("Period");
    }

    isExtraOptionFilterShown(option) {
        const data = this.filterExtraOptionsData[option];
        return (
            option in this.controller.cachedFilterOptions &&
            option in this.filterExtraOptionsData &&
            data.show !== false &&
            (data.group === undefined || this.controller.cachedUserGroups[data.group])
        );
    }

    get hasExtraOptionsFilter() {
        return Object.keys(this.filterExtraOptionsData).some((option) =>
            this.isExtraOptionFilterShown(option),
        );
    }

    get hasUIFilter() {
        return Object.entries(this.filterExtraOptionsData).some(
            ([option, data]) => data.ui_filter && this.isExtraOptionFilterShown(option),
        );
    }

    dateFrom(optionKey) {
        return DateTime.fromISO(
            this.controller.cachedFilterOptions[optionKey].date_from,
        );
    }

    dateTo(optionKey) {
        return DateTime.fromISO(this.controller.cachedFilterOptions[optionKey].date_to);
    }

    // Setters
    setDate(optionKey, type, date) {
        if (date) {
            this.controller.cachedFilterOptions[optionKey][`date_${type}`] = date;
            this.applyFilters(optionKey);
        } else {
            this.dialog.add(WarningDialog, {
                title: _t("Odoo Warning"),
                message: _t("Date cannot be empty"),
            });
        }
    }

    setDateFrom(optionKey, dateFrom) {
        this.setDate(optionKey, "from", dateFrom);
    }

    setDateTo(optionKey, dateTo) {
        this.setDate(optionKey, "to", dateTo);
    }

    dateFilters(mode) {
        switch (mode) {
            case "single":
                return [
                    {
                        name: _t("End of Month"),
                        period: "month",
                        mode: this.dateFilter.editing === "month" ? "edit" : "view",
                    },
                    {
                        name: _t("End of Quarter"),
                        period: "quarter",
                        mode: this.dateFilter.editing === "quarter" ? "edit" : "view",
                    },
                    {
                        name: _t("End of Year"),
                        period: "year",
                        mode: this.dateFilter.editing === "year" ? "edit" : "view",
                    },
                ];
            case "range":
                return [
                    {
                        name: _t("Month"),
                        period: "month",
                        mode: this.dateFilter.editing === "month" ? "edit" : "view",
                    },
                    {
                        name: _t("Quarter"),
                        period: "quarter",
                        mode: this.dateFilter.editing === "quarter" ? "edit" : "view",
                    },
                    {
                        name: _t("Year"),
                        period: "year",
                        mode: this.dateFilter.editing === "year" ? "edit" : "view",
                    },
                ];
            default:
                throw new Error(`Invalid mode in dateFilters(): ${mode}`);
        }
    }

    initDateFilters() {
        const filters = { editing: false };
        for (const periodType of Object.keys(this.periodHandlers)) {
            filters[periodType] = 0;
        }

        const specifier = this.controller.cachedFilterOptions.date.filter.split("_")[0];
        const periodType = this.controller.cachedFilterOptions.date.period_type;
        // In case the period is fiscalyear it will be computed exactly like a year period.
        const period = periodType === "fiscalyear" ? "year" : periodType;
        // Set the filter value based on the specifier.
        if (Object.prototype.hasOwnProperty.call(filters, period)) {
            filters[period] =
                this.controller.cachedFilterOptions.date.period ||
                (specifier === "previous" ? -1 : specifier === "next" ? 1 : 0);
        }

        return filters;
    }

    getDateFilter(periodType) {
        if (this.dateFilter[periodType] > 0) {
            return `next_${periodType}`;
        } else if (this.dateFilter[periodType] === 0) {
            return `this_${periodType}`;
        } else if (this.dateFilter[periodType] < 0) {
            return `previous_${periodType}`;
        } else {
            return periodType;
        }
    }

    selectDateFilter(periodType, reload = false) {
        if (this.isPeriodSelected(periodType)) {
            return;
        }
        this.dateFilter.editing = false;
        const offsetPeriod = Object.prototype.hasOwnProperty.call(
            this.dateFilter,
            periodType,
        );
        this.filterClicked({
            optionKey: "date.filter",
            optionValue: this.getDateFilter(periodType),
            reload: !offsetPeriod && reload,
        });
        if (offsetPeriod) {
            this.filterClicked({
                optionKey: "date.period",
                optionValue: this.dateFilter[periodType],
                reload: reload,
            });
        }
    }

    editDateFilter(periodType, inputField) {
        inputField?.select();
        this.dateFilter.editing = periodType;
    }

    saveDateFilter(periodType, inputField) {
        if (!this.dateFilter.editing) {
            return;
        }
        const enteredValue = inputField?.value;
        const handler = this.periodHandlers[periodType];
        let dateFilterOffset = handler ? handler.parse(enteredValue) : false;
        if (dateFilterOffset !== false) {
            dateFilterOffset -= this.dateFilter[periodType];
            this._changePeriod(periodType, dateFilterOffset);
        }
        inputField?.setSelectionRange(enteredValue.length, enteredValue.length);
        this.dateFilter.editing = false;
    }

    _parseMonthOffset(input) {
        try {
            const monthTo = parseDate(input.trim(), { format: "MMMM yyyy" });
            if (!monthTo.isValid) {
                return false;
            }
            const compareDate = DateTime.now().startOf("month");
            return monthTo.startOf("month").diff(compareDate, "months").months;
        } catch {
            return false;
        }
    }

    _parseQuarterOffset(input) {
        try {
            const quarterTo = parseDate(input.split("-").pop().trim(), {
                format: "MMM yyyy",
            });
            if (!quarterTo.isValid) {
                return false;
            }
            const compareDate = DateTime.now().startOf("quarter");
            return quarterTo.startOf("quarter").diff(compareDate, "quarters").quarters;
        } catch {
            return false;
        }
    }

    _parseYearOffset(input) {
        try {
            const yearTo = parseDate(input, { format: "yyyy" });
            if (!yearTo.isValid) {
                return false;
            }
            const compareDate = DateTime.now().startOf("year");
            return yearTo.startOf("year").diff(compareDate, "years").years;
        } catch {
            return false;
        }
    }

    selectPreviousPeriod(periodType) {
        this._changePeriod(periodType, -1);
    }

    selectNextPeriod(periodType) {
        this._changePeriod(periodType, 1);
    }

    _changePeriod(periodType, increment) {
        this.dateFilter[periodType] = this.dateFilter[periodType] + increment;

        this.controller.updateOption("date.filter", this.getDateFilter(periodType));
        this.controller.updateOption("date.period", this.dateFilter[periodType]);

        this.applyFilters("date.period");
    }

    isPeriodSelected(periodType) {
        return this.controller.cachedFilterOptions.date.filter.endsWith(periodType);
    }

    displayPeriod(periodType) {
        const handler = this.periodHandlers[periodType];
        if (!handler) {
            throw new Error(`Invalid period type in displayPeriod(): ${periodType}`);
        }
        return handler.display(DateTime.now());
    }

    _displayMonth(dateTo) {
        return dateTo.plus({ months: this.dateFilter.month }).toFormat("MMMM yyyy");
    }

    _displayQuarter(dateTo) {
        const quarterMonths = {
            1: { start: 1, end: 3 },
            2: { start: 4, end: 6 },
            3: { start: 7, end: 9 },
            4: { start: 10, end: 12 },
        };

        dateTo = dateTo.plus({ months: this.dateFilter.quarter * 3 });

        const quarterDateFrom = DateTime.utc(
            dateTo.year,
            quarterMonths[dateTo.quarter]["start"],
            1,
        );
        const quarterDateTo = DateTime.utc(
            dateTo.year,
            quarterMonths[dateTo.quarter]["end"],
            1,
        );

        return `${formatDate(quarterDateFrom, { format: "MMM" })} - ${formatDate(quarterDateTo, { format: "MMM yyyy" })}`;
    }

    _displayYear(dateTo) {
        return dateTo.plus({ years: this.dateFilter.year }).toFormat("yyyy");
    }

    /**
     * Must stay consistent with `AccountReturnType._get_period_boundaries` in
     * `account/models/account_return.py`.
     */
    //------------------------------------------------------------------------------------------------------------------
    // Number of periods
    //------------------------------------------------------------------------------------------------------------------
    setNumberPeriods(ev) {
        const numberPeriods = ev.target.value;

        if (numberPeriods >= 1) {
            this.controller.cachedFilterOptions.comparison.number_period =
                parseInt(numberPeriods);
        } else {
            this.dialog.add(WarningDialog, {
                title: _t("Odoo Warning"),
                message: _t("Number of periods cannot be smaller than 1"),
            });
        }
    }

    //------------------------------------------------------------------------------------------------------------------
    // Records
    //------------------------------------------------------------------------------------------------------------------
    getMultiRecordSelectorProps(resModel, optionKey) {
        return {
            resModel,
            resIds: this.controller.cachedFilterOptions[optionKey],
            update: (resIds) => {
                this.filterClicked({
                    optionKey: optionKey,
                    optionValue: resIds,
                    reload: true,
                });
            },
        };
    }

    //------------------------------------------------------------------------------------------------------------------
    // Rounding unit
    //------------------------------------------------------------------------------------------------------------------
    roundingUnitName(roundingUnit) {
        return _t(
            "In %s",
            this.controller.cachedFilterOptions["rounding_unit_names"][roundingUnit][0],
        );
    }

    //------------------------------------------------------------------------------------------------------------------
    // Generic filters
    //------------------------------------------------------------------------------------------------------------------
    async filterClicked({ optionKey, optionValue = undefined, reload = false }) {
        if (optionValue !== undefined) {
            await this.controller.updateOption(optionKey, optionValue);
        } else {
            await this.controller.toggleOption(optionKey);
        }

        if (reload) {
            await this.applyFilters(optionKey);
        }
    }

    async applyFilters(optionKey = null, delay = 500) {
        // We only call the reload after the delay is finished, to avoid doing 5 calls if you want to click on 5 journals
        if (this.timeout) {
            clearTimeout(this.timeout);
        }

        this.controller.incrementCallNumber();

        this.timeout = setTimeout(async () => {
            if (status(this) !== "destroyed") {
                await this.controller.reload(
                    optionKey,
                    this.controller.cachedFilterOptions,
                );
            }
        }, delay);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Custom filters
    //------------------------------------------------------------------------------------------------------------------
    async filterVariant(reportId) {
        this.controller.saveSessionOptions({
            ...this.controller.cachedFilterOptions,
            selected_variant_id: reportId,
            sections_source_id: reportId,
        });
        const cacheKey = this.controller.getCacheKey(reportId, reportId);
        // if the variant hasn't been loaded yet, set up the call number
        if (!(cacheKey in this.controller.loadingCallNumberByCacheKey)) {
            this.controller.incrementCallNumber(cacheKey);
        }
        await this.controller.displayReport(reportId);
    }

    async toggleHideZeroLines() {
        // Avoid calling the database when this filter is toggled; as the exact same lines would be returned; just reassign visibility.
        await this.controller.toggleOption("hide_0_lines", false);

        this.controller.saveSessionOptions(this.controller.cachedFilterOptions);
        this.controller.setLineVisibility(this.controller.lines);
    }

    async toggleHorizontalSplit() {
        await this.controller.toggleOption("horizontal_split", false);
        this.controller.saveSessionOptions(this.controller.cachedFilterOptions);
    }

    async filterRoundingUnit(rounding) {
        await this.controller.updateOption("rounding_unit", rounding, false);

        this.controller.saveSessionOptions(this.controller.cachedFilterOptions);

        this.controller.lines = await this.controller.orm.call(
            "account.report",
            "dispatch_report_action",
            [
                this.controller.cachedFilterOptions.report_id,
                this.controller.cachedFilterOptions,
                "format_column_values_from_client",
                this.controller.lines,
            ],
            {
                context: this.controller.context,
            },
        );
    }
}
