import { _t } from "@web/core/l10n/translation";
import { status, Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { WarningDialog } from "@web/core/errors/error_dialogs";

import { DateTimeInput } from '@web/core/datetime/datetime_input';
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { formatDate} from "@web/core/l10n/dates";
const { DateTime } = luxon;

export class AccountReportFilters extends Component {
    static template = "account_reports.AccountReportFilters";
    static props = {};
    static components = {
        DateTimeInput,
        Dropdown,
        DropdownItem,
        MultiRecordSelector,
    };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.companyService = useService("company");
        this.controller = useState(this.env.controller);
        if (this.env.controller.options.date) {
            this.dateFilter = useState(this.initDateFilters());
        }
        this.budgetName = useState({
            value: "",
            invalid: false,
        });
        this.timeout = null;
    }

    focusInnerInput(index, items) {
        const selectedItem = items[index];
        selectedItem.el.querySelector(":scope input")?.focus();
    }

    //------------------------------------------------------------------------------------------------------------------
    // Getters
    //------------------------------------------------------------------------------------------------------------------
    get selectedFiscalPositionName() {
        switch (this.controller.options.fiscal_position) {
            case "domestic":
                return _t("Domestic");
            case "all":
                return _t("All");
            default:
                for (const fiscalPosition of this.controller.options.available_vat_fiscal_positions) {
                    if (fiscalPosition.id === this.controller.options.fiscal_position) {
                        return fiscalPosition.name;
                    }
                }
        }
        return _t("None");
    }

    get selectedHorizontalGroupName() {
        for (const horizontalGroup of this.controller.options.available_horizontal_groups) {
            if (horizontalGroup.id === this.controller.options.selected_horizontal_group_id) {
                return horizontalGroup.name;
            }
        }
        return _t("None");
    }

    get isHorizontalGroupSelected() {
        return this.controller.options.available_horizontal_groups.some((group) => {
            return group.id === this.controller.options.selected_horizontal_group_id;
        });
    }

    get selectedTaxUnitName() {
        for (const taxUnit of this.controller.options.available_tax_units) {
            if (taxUnit.id === this.controller.options.tax_unit) {
                return taxUnit.name;
            }
        }
        return _t("Company Only");
    }

    get selectedVariantName() {
        for (const variant of this.controller.options.available_variants) {
            if (variant.id === this.controller.options.selected_variant_id) {
                return variant.name;
            }
        }
        return _t("None");
    }

    get selectedSectionName() {
        for (const section of this.controller.options.sections)
            if (section.id === this.controller.options.selected_section_id)
                return section.name;
    }

    get selectedAccountType() {
        let selectedAccountType = this.controller.options.account_type.filter(
            (accountType) => accountType.selected,
        );
        if (
            !selectedAccountType.length ||
            selectedAccountType.length === this.controller.options.account_type.length
        ) {
            return _t("All");
        }

        const accountTypeMappings = [
            { list: ["trade_receivable", "non_trade_receivable"], name: _t("All Receivable") },
            { list: ["trade_payable", "non_trade_payable"], name: _t("All Payable") },
            { list: ["trade_receivable", "trade_payable"], name: _t("Trade Partners") },
            { list: ["non_trade_receivable", "non_trade_payable"], name: _t("Non Trade Partners") },
        ];

        const listToDisplay = [];
        for (const mapping of accountTypeMappings) {
            if (
                mapping.list.every((accountType) =>
                    selectedAccountType.map((accountType) => accountType.id).includes(accountType),
                )
            ) {
                listToDisplay.push(mapping.name);
                // Delete already checked id
                selectedAccountType = selectedAccountType.filter(
                    (accountType) => !mapping.list.includes(accountType.id),
                );
            }
        }

        return listToDisplay
            .concat(selectedAccountType.map((accountType) => accountType.name))
            .join(", ");
    }

    get selectedAmlIrFilters() {
        const selectedFilters = this.controller.options.aml_ir_filters.filter(
            (irFilter) => irFilter.selected,
        );

        if (selectedFilters.length === 1) {
            return selectedFilters[0].name;
        } else if (selectedFilters.length > 1) {
            return _t("%s selected", selectedFilters.length);
        } else {
            return _t("None");
        }
    }

    get availablePeriodOrder() {
        return { descending: _t("Descending"), ascending: _t("Ascending") };
    }

    get periodOrder() {
        return this.controller.options.comparison.period_order === "descending"
            ? _t("Descending")
            : _t("Ascending");
    }

    get selectedExtraOptions() {
        const selectedExtraOptions = [];

        if (this.controller.groups.account_readonly && this.controller.filters.show_draft) {
            selectedExtraOptions.push(
                this.controller.options.all_entries
                    ? _t("With Draft Entries")
                    : _t("Posted Entries"),
            );
        }
        if (this.controller.filters.show_unreconciled && this.controller.options.unreconciled) {
            selectedExtraOptions.push(_t("Unreconciled Entries"));
        }
        if (this.controller.options.include_analytic_without_aml) {
            selectedExtraOptions.push(_t("Including Analytic Simulations"));
        }
        return selectedExtraOptions.join(", ");
    }

    get dropdownProps() {
        return {
            shouldFocusChildInput: false,
            hotkeys: {
                arrowright: (index, items) => this.focusInnerInput(index, items),
            },
        };
    }

    get periodLabel() {
        return this.controller.options.comparison.number_period > 1 ? _t("Periods") : _t("Period");
    }
    //------------------------------------------------------------------------------------------------------------------
    // Helpers
    //------------------------------------------------------------------------------------------------------------------
    get hasAnalyticGroupbyFilter() {
        return Boolean(this.controller.groups.analytic_accounting) && (Boolean(this.controller.filters.show_analytic_groupby) || Boolean(this.controller.filters.show_analytic_plan_groupby));
    }

    get hasCodesFilter() {
        return Boolean(this.controller.options.sales_report_taxes?.operation_category?.goods);
    }

    get hasExtraOptionsFilter() {
        return (
            "report_cash_basis" in this.controller.options ||
            this.controller.filters.show_draft ||
            this.controller.filters.show_all ||
            this.controller.filters.show_unreconciled ||
            this.hasUIFilter
        );
    }

    get hasUIFilter() {
        return (
            this.controller.filters.show_hide_0_lines !== "never" ||
            "horizontal_split" in this.controller.options
        );
    }

    get hasFiscalPositionFilter() {
        const isMultiCompany = this.controller.options.companies.length > 1;
        const minimumFiscalPosition = this.controller.options.allow_domestic ? 0 : 1;
        const hasFiscalPositions =
            this.controller.options.available_vat_fiscal_positions.length > minimumFiscalPosition;
        return hasFiscalPositions && isMultiCompany;
    }

    get isBudgetSelected() {
        return this.controller.options.budgets?.some((budget) => {
            return budget.selected;
        });
    }

    //------------------------------------------------------------------------------------------------------------------
    // Dates
    //------------------------------------------------------------------------------------------------------------------
    // Getters
    dateFrom(optionKey) {
        return DateTime.fromISO(this.controller.options[optionKey].date_from);
    }

    dateTo(optionKey) {
        return DateTime.fromISO(this.controller.options[optionKey].date_to);
    }

    // Setters
    setDate(optionKey, type, date) {
        if (date) {
            this.controller.options[optionKey][`date_${type}`] = date;
            this.applyFilters(optionKey);
        }
        else {
            this.dialog.add(WarningDialog, {
                title: _t("Odoo Warning"),
                message: _t("Date cannot be empty"),
            });
        }
    }

    setDateFrom(optionKey, dateFrom) {
        this.setDate(optionKey, 'from', dateFrom);
    }

    setDateTo(optionKey, dateTo) {
        this.setDate(optionKey, 'to', dateTo);
    }

    dateFilters(mode) {
        switch (mode) {
            case "single":
                return [
                    {"name": _t("End of Month"), "period": "month"},
                    {"name": _t("End of Quarter"), "period": "quarter"},
                    {"name": _t("End of Year"), "period": "year"},
                ];
            case "range":
                return [
                    {"name": _t("Month"), "period": "month"},
                    {"name": _t("Quarter"), "period": "quarter"},
                    {"name": _t("Year"), "period": "year"},
                ];
            default:
                throw new Error(`Invalid mode in dateFilters(): ${ mode }`);
        }
    }

    initDateFilters() {
        const filters = {
            "month": 0,
            "quarter": 0,
            "year": 0,
            "tax_period": 0
        };

        const specifier = this.controller.options.date.filter.split('_')[0];
        const periodType = this.controller.options.date.period_type;
        // In case the period is fiscalyear it will be computed exactly like a year period.
        const period = periodType === "fiscalyear" ? "year" : periodType;
        // Set the filter value based on the specifier
        filters[period] = this.controller.options.date.period || (specifier === 'previous' ? -1 : specifier === 'next' ? 1 : 0);

        return filters;
    }

    getDateFilter(periodType) {
        if (this.dateFilter[periodType] > 0) {
            return `next_${periodType}`;
        } else if (this.dateFilter[periodType] === 0) {
            return `this_${periodType}`;
        } else {
            return `previous_${periodType}`;
        }
    }

    selectDateFilter(periodType, reload = false) {
        this.filterClicked({ optionKey: "date.filter", optionValue: this.getDateFilter(periodType)});
        this.filterClicked({ optionKey: "date.period", optionValue: this.dateFilter[periodType], reload: reload});
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
        return this.controller.options.date.filter.includes(periodType)
    }

    displayPeriod(periodType) {
        const dateTo = DateTime.now();

        switch (periodType) {
            case "month":
                return this._displayMonth(dateTo);
            case "quarter":
                return this._displayQuarter(dateTo);
            case "year":
                return this._displayYear(dateTo);
            case "tax_period":
                return this._displayTaxPeriod(dateTo);
            default:
                throw new Error(`Invalid period type in displayPeriod(): ${ periodType }`);
        }
    }

    _displayMonth(dateTo) {
        return dateTo.plus({ months: this.dateFilter.month }).toFormat("MMMM yyyy");
    }

    _displayQuarter(dateTo) {
        const quarterMonths = {
            1: { 'start': 1, 'end': 3 },
            2: { 'start': 4, 'end': 6 },
            3: { 'start': 7, 'end': 9 },
            4: { 'start': 10, 'end': 12 },
        }

        dateTo = dateTo.plus({ months: this.dateFilter.quarter * 3 });

        const quarterDateFrom = DateTime.utc(dateTo.year, quarterMonths[dateTo.quarter]['start'], 1)
        const quarterDateTo = DateTime.utc(dateTo.year, quarterMonths[dateTo.quarter]['end'], 1)

        return `${ formatDate(quarterDateFrom, {format: "MMM"}) } - ${ formatDate(quarterDateTo, {format: "MMM yyyy"}) }`;
    }

    _displayYear(dateTo) {
        return dateTo.plus({ years: this.dateFilter.year }).toFormat("yyyy");
    }

    _displayTaxPeriod(dateTo) {
        const periodicitySettings = this.controller.options.tax_periodicity;
        const targetDateInPeriod = dateTo.plus({months: periodicitySettings.months_per_period * this.dateFilter['tax_period']})
        const [start, end] = this._computeTaxPeriodDates(periodicitySettings, targetDateInPeriod);

        if (periodicitySettings.start_month == 1 && periodicitySettings.start_day == 1) {
            switch (periodicitySettings.months_per_period) {
                case 1: return end.toFormat("MMMM yyyy");
                case 3: return `Q${end.quarter} ${dateTo.year}`;
                case 12: return end.toFormat("yyyy");
            }
        }

        return formatDate(start) + ' - ' + formatDate(end);
    }

    _computeTaxPeriodDates(periodicitySettings, dateInsideTargettesPeriod) {
        /**
         * This function need to stay consitent with the one inside res_company from module account_reports.
         * function_name = _get_tax_closing_period_boundaries
         */
        const startMonth = periodicitySettings.start_month;
        const startDay = periodicitySettings.start_day
        const monthsPerPeriod = periodicitySettings.months_per_period;
        const aligned_date = dateInsideTargettesPeriod.minus({days: startDay - 1}) 
        let year = aligned_date.year;
        const monthOffset = aligned_date.month - startMonth;

        let periodNumber = Math.floor(monthOffset / monthsPerPeriod) + 1;

        if (dateInsideTargettesPeriod < DateTime.now().set({year: year, month: startMonth, day: startDay})) {
            year -= 1;
            periodNumber = Math.floor((12 + monthOffset) / monthsPerPeriod) + 1;
        }

        let deltaMonth = periodNumber * monthsPerPeriod;

        const endDate = DateTime.utc(year, startMonth, 1).plus({ months: deltaMonth, days: startDay-2})
        const startDate = DateTime.utc(year, startMonth, 1).plus({ months: deltaMonth-monthsPerPeriod }).set({ day: startDay})
        return [startDate, endDate];
    }

    //------------------------------------------------------------------------------------------------------------------
    // Number of periods
    //------------------------------------------------------------------------------------------------------------------
    setNumberPeriods(ev) {
        const numberPeriods = ev.target.value;

        if (numberPeriods >= 1)
            this.controller.options.comparison.number_period = parseInt(numberPeriods);
        else
            this.dialog.add(WarningDialog, {
                title: _t("Odoo Warning"),
                message: _t("Number of periods cannot be smaller than 1"),
            });
    }

    //------------------------------------------------------------------------------------------------------------------
    // Records
    //------------------------------------------------------------------------------------------------------------------
    getMultiRecordSelectorProps(resModel, optionKey) {
        return {
            resModel,
            resIds: this.controller.options[optionKey],
            update: (resIds) => {
                this.filterClicked({ optionKey: optionKey, optionValue: resIds, reload: true});
            },
        };
    }

    //------------------------------------------------------------------------------------------------------------------
    // Rounding unit
    //------------------------------------------------------------------------------------------------------------------
    roundingUnitName(roundingUnit) {
        return _t("In %s", this.controller.options["rounding_unit_names"][roundingUnit][0]);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Generic filters
    //------------------------------------------------------------------------------------------------------------------
    async filterClicked({ optionKey, optionValue = undefined, reload = false}) {
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

        this.controller.loadingCallNumber++;

        this.timeout = setTimeout(async () => {
            if (status(this) !== "destroyed") 
                await this.controller.reload(optionKey, this.controller.options);
        }, delay);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Custom filters
    //------------------------------------------------------------------------------------------------------------------
    selectJournal(journal) {
        if (journal.model === "account.journal.group") {
            const wasSelected = journal.selected;
            this.ToggleSelectedJournal(journal);
            this.controller.options.__journal_group_action = {
                action: wasSelected ? "remove" : "add",
                id: parseInt(journal.id),
            };
            // Toggle the selected status after the action is set
            journal.selected = !wasSelected;
        } else {
            journal.selected = !journal.selected;
        }
        this.applyFilters("journals");
    }

    ToggleSelectedJournal(selectedJournal) {
        if (selectedJournal.selected) {
            this.controller.options.journals.forEach((journal) => {
                journal.selected = false;
            });
        } else {
            this.controller.options.journals.forEach((journal) => {
                journal.selected = selectedJournal.journals.includes(journal.id) && journal.model === "account.journal";
            });
        }
    }

    unfoldCompanyJournals(selectedCompany) {
        let inSelectedCompanySection = false;
        for (const journal of this.controller.options.journals) {
            if (journal.id === "divider" && journal.model === "res.company") {
                if (journal.name === selectedCompany.name) {
                    journal.unfolded = !journal.unfolded;
                    inSelectedCompanySection = true;
                } else if (inSelectedCompanySection) {
                    break;  // Reached another company divider, exit the loop
                }
            }
            if (inSelectedCompanySection && journal.model === "account.journal") {
                journal.visible = !journal.visible;
            }
        }
    }

    async filterVariant(reportId) {
        this.controller.saveSessionOptions({
            ...this.controller.options,
            selected_variant_id: reportId,
            sections_source_id: reportId,
        });
        await this.controller.displayReport(reportId);
    }

    async filterTaxUnit(taxUnit) {
        await this.filterClicked({ optionKey: "tax_unit", optionValue: taxUnit.id});
        this.controller.saveSessionOptions(this.controller.options);

        // force the company to those impacted by the tax units, the reload will be force by this function
        this.companyService.setCompanies(taxUnit.company_ids);
    }

    async toggleHideZeroLines() {
        // Avoid calling the database when this filter is toggled; as the exact same lines would be returned; just reassign visibility.
        await this.controller.toggleOption("hide_0_lines", false);

        this.controller.saveSessionOptions(this.controller.options);
        this.controller.setLineVisibility(this.controller.lines);
    }

    async toggleHorizontalSplit() {
        await this.controller.toggleOption("horizontal_split", false);
        this.controller.saveSessionOptions(this.controller.options);
    }

    async filterRoundingUnit(rounding) {
        await this.controller.updateOption('rounding_unit', rounding, false);

        this.controller.saveSessionOptions(this.controller.options);

        this.controller.lines = await this.controller.orm.call(
            "account.report",
            "dispatch_report_action",
            [
                this.controller.options.report_id,
                this.controller.options,
                "format_column_values_from_client",
                this.controller.lines,
            ],
            {
                context: this.controller.context,
            }
        );
    }

    async selectHorizontalGroup(horizontalGroupId) {
        if (horizontalGroupId === this.controller.options.selected_horizontal_group_id) {
            return;
        }

        if (this.isBudgetSelected) {
            this.notification.add(
                _t("It's not possible to select a budget with the horizontal group feature."),
                {
                    type: "warning",
                }
            );
            return;
        }
        await this.filterClicked({ optionKey: "selected_horizontal_group_id", optionValue: horizontalGroupId, reload: true});
    }

    selectBudget(budget) {
        if (this.isHorizontalGroupSelected) {
            this.notification.add(
                _t("It's not possible to select a horizontal group with the budget feature."),
                {
                    type: "warning",
                }
            );
            return;
        }
        budget.selected = !budget.selected;
        this.applyFilters( 'budgets')
    }

    async createBudget() {
        const budgetName = this.budgetName.value.trim();
        if (!budgetName.length) {
            this.budgetName.invalid = true;
            this.notification.add(_t("Please enter a valid budget name."), {
                type: "danger",
            });
            return;
        }
        const createdId = await this.orm.call("account.report.budget", "create", [
            { name: budgetName },
        ]);
        this.budgetName.value = "";
        this.budgetName.invalid = false;
        const options = this.controller.options;
        this.controller.reload("budgets", {
            ...options,
            budgets: [
                ...options.budgets,
                // Selected by default if we don't have any horizontal group selected
                { id: createdId, selected: !this.isHorizontalGroupSelected },
            ],
        });
    }
}
