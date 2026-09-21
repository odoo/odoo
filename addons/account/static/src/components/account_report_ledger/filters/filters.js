/** @odoo-module native */
import { AccountReportFilters } from "@account/components/account_report/filters/filters";
import { useState } from "@odoo/owl";
import { formatDate, parseDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

import { DateTime } from "luxon";

patch(AccountReportFilters.prototype, {
    setup() {
        super.setup();
        this.budgetName = useState({
            value: "",
            invalid: false,
        });
    },

    get filterExtraOptionsData() {
        const { unfold_all, integer_rounding_enabled, ...uiOptions } = super
            .filterExtraOptionsData;
        return {
            all_entries: {
                name: _t("Draft Entries"),
                group: "account_readonly",
                show: this.controller.filters.show_draft,
            },
            include_analytic_without_aml: {
                name: _t("Analytic Simulations"),
                group: "account_readonly",
            },
            hierarchy: {
                name: _t("Hierarchy and Subtotals"),
                show: this.controller.cachedFilterOptions.display_hierarchy_filter,
            },
            unreconciled: {
                name: _t("Unreconciled Entries"),
                show: this.controller.filters.show_unreconciled,
            },
            unfold_all,
            integer_rounding_enabled,
            consolidation: {
                name: _t("Consolidation"),
                show: this.controller.cachedFilterOptions.show_consolidation,
            },
            ...uiOptions,
        };
    },

    get periodHandlers() {
        return {
            ...super.periodHandlers,
            return_period: {
                parse: (input) => this._parseReturnPeriodOffset(input),
                display: (dateTo) =>
                    this.controller.cachedFilterOptions.return_periodicity
                        ? this._displayReturnPeriod(dateTo)
                        : this._displayMonth(dateTo),
            },
        };
    },

    get selectedHorizontalGroupName() {
        for (const horizontalGroup of this.controller.cachedFilterOptions
            .available_horizontal_groups) {
            if (
                horizontalGroup.id ===
                this.controller.cachedFilterOptions.selected_horizontal_group_id
            ) {
                return horizontalGroup.name;
            }
        }
        return _t("None");
    },

    get isHorizontalGroupSelected() {
        return this.controller.cachedFilterOptions.available_horizontal_groups.some(
            (group) =>
                group.id ===
                this.controller.cachedFilterOptions.selected_horizontal_group_id,
        );
    },

    get selectedTaxUnitName() {
        for (const taxUnit of this.controller.cachedFilterOptions.available_tax_units) {
            if (taxUnit.id === this.controller.cachedFilterOptions.tax_unit) {
                return taxUnit.name;
            }
        }
        return _t("Company Only");
    },

    get selectedAccountType() {
        let selectedAccountType =
            this.controller.cachedFilterOptions.account_type.filter(
                (accountType) => accountType.selected,
            );
        if (
            !selectedAccountType.length ||
            selectedAccountType.length ===
                this.controller.cachedFilterOptions.account_type.length
        ) {
            return _t("All");
        }

        const accountTypeMappings = [
            {
                list: ["trade_receivable", "non_trade_receivable"],
                name: _t("All Receivable"),
            },
            { list: ["trade_payable", "non_trade_payable"], name: _t("All Payable") },
            { list: ["trade_receivable", "trade_payable"], name: _t("Trade Partners") },
            {
                list: ["non_trade_receivable", "non_trade_payable"],
                name: _t("Non Trade Partners"),
            },
        ];

        const listToDisplay = [];
        for (const mapping of accountTypeMappings) {
            if (
                mapping.list.every((accountType) =>
                    selectedAccountType
                        .map((accountType) => accountType.id)
                        .includes(accountType),
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
    },

    get selectedAmlIrFilters() {
        const selectedFilters =
            this.controller.cachedFilterOptions.aml_ir_filters.filter(
                (irFilter) => irFilter.selected,
            );

        if (selectedFilters.length === 1) {
            return selectedFilters[0].name;
        } else if (selectedFilters.length > 1) {
            return _t("%s selected", selectedFilters.length);
        } else {
            return _t("None");
        }
    },

    get selectedExtraOptions() {
        const selectedExtraOptions = [];

        if (
            this.controller.cachedUserGroups.account_readonly &&
            this.controller.filters.show_draft
        ) {
            selectedExtraOptions.push(
                this.controller.cachedFilterOptions.all_entries
                    ? _t("With Draft Entries")
                    : _t("Posted Entries"),
            );
        }
        if (
            this.controller.filters.show_unreconciled &&
            this.controller.cachedFilterOptions.unreconciled
        ) {
            selectedExtraOptions.push(_t("Unreconciled Entries"));
        }
        if (this.controller.cachedFilterOptions.include_analytic_without_aml) {
            selectedExtraOptions.push(_t("Including Analytic Simulations"));
        }
        return selectedExtraOptions.join(", ");
    },

    get hasAnalyticGroupbyFilter() {
        return (
            Boolean(this.controller.cachedUserGroups.analytic_accounting) &&
            (Boolean(this.controller.filters.show_analytic_groupby) ||
                Boolean(this.controller.filters.show_analytic_plan_groupby))
        );
    },

    get hasCodesFilter() {
        return Boolean(
            this.controller.cachedFilterOptions.sales_report_taxes?.operation_category
                ?.goods,
        );
    },

    get isBudgetSelected() {
        return this.controller.cachedFilterOptions.budgets?.some(
            (budget) => budget.selected,
        );
    },

    _parseReturnPeriodOffset(input) {
        try {
            const dateTo = parseDate(input.split("-").pop().trim());
            if (!dateTo.isValid) {
                return false;
            }
            const periodicitySettings =
                this.controller.cachedFilterOptions.return_periodicity;
            const [, compareTo] = this._computeReturnPeriodDates(
                periodicitySettings,
                DateTime.now(),
            );
            const [, taxPeriodTo] = this._computeReturnPeriodDates(
                periodicitySettings,
                dateTo,
            );
            return (
                taxPeriodTo.startOf("month").diff(compareTo.startOf("month"), "months")
                    .months / periodicitySettings.months_per_period
            );
        } catch {
            return false;
        }
    },

    get shouldDisplayReturnPeriod() {
        const periodicitySettings =
            this.controller.cachedFilterOptions.return_periodicity;
        return periodicitySettings?.is_filter_visible ?? false;
    },

    _displayReturnPeriod(dateTo) {
        const periodicitySettings =
            this.controller.cachedFilterOptions.return_periodicity;
        const targetDateInPeriod = dateTo.plus({
            months:
                periodicitySettings.months_per_period *
                this.dateFilter["return_period"],
        });
        const [start, end] = this._computeReturnPeriodDates(
            periodicitySettings,
            targetDateInPeriod,
        );
        return formatDate(start) + " - " + formatDate(end);
    },

    _computeReturnPeriodDates(periodicitySettings, dateInsideTargettesPeriod) {
        const startMonth = periodicitySettings.start_month;
        const startDay = periodicitySettings.start_day;
        const monthsPerPeriod = periodicitySettings.months_per_period;
        const aligned_date = dateInsideTargettesPeriod.minus({ days: startDay - 1 });
        let year = aligned_date.year;
        const monthOffset = aligned_date.month - startMonth;

        let periodNumber = Math.floor(monthOffset / monthsPerPeriod) + 1;

        if (
            dateInsideTargettesPeriod <
            DateTime.now().set({ year: year, month: startMonth, day: startDay })
        ) {
            year -= 1;
            periodNumber = Math.floor((12 + monthOffset) / monthsPerPeriod) + 1;
        }

        const deltaMonth = periodNumber * monthsPerPeriod;

        const endDate = DateTime.utc(year, startMonth, 1).plus({
            months: deltaMonth,
            days: startDay - 2,
        });
        const startDate = DateTime.utc(year, startMonth, 1)
            .plus({ months: deltaMonth - monthsPerPeriod })
            .set({ day: startDay });
        return [startDate, endDate];
    },

    selectJournal(journal) {
        if (journal.model === "account.journal.group") {
            const wasSelected = journal.selected;
            this.ToggleSelectedJournal(journal);
            this.controller.cachedFilterOptions.__journal_group_action = {
                action: wasSelected ? "remove" : "add",
                id: parseInt(journal.id),
            };
            // Toggle the selected status after the action is set
            journal.selected = !wasSelected;
        } else {
            journal.selected = !journal.selected;
        }
        this.applyFilters("journals");
    },

    ToggleSelectedJournal(selectedJournal) {
        if (selectedJournal.selected) {
            this.controller.cachedFilterOptions.journals.forEach((journal) => {
                journal.selected = false;
            });
        } else {
            this.controller.cachedFilterOptions.journals.forEach((journal) => {
                journal.selected =
                    selectedJournal.journals.includes(journal.id) &&
                    journal.model === "account.journal";
            });
        }
    },

    unfoldCompanyJournals(selectedCompany) {
        let inSelectedCompanySection = false;
        for (const journal of this.controller.cachedFilterOptions.journals) {
            if (journal.id === "divider" && journal.model === "res.company") {
                if (journal.name === selectedCompany.name) {
                    journal.unfolded = !journal.unfolded;
                    inSelectedCompanySection = true;
                } else if (inSelectedCompanySection) {
                    break; // Reached another company divider, exit the loop
                }
            }
            if (inSelectedCompanySection && journal.model === "account.journal") {
                journal.visible = !journal.visible;
            }
        }
    },

    async filterTaxUnit(taxUnit) {
        await this.filterClicked({ optionKey: "tax_unit", optionValue: taxUnit.id });
        this.controller.saveSessionOptions(this.controller.cachedFilterOptions);

        // Restrict the active companies to those impacted by the tax unit; this call forces the reload.
        user.activateCompanies(taxUnit.company_ids);
    },

    async selectHorizontalGroup(horizontalGroupId) {
        if (
            horizontalGroupId ===
            this.controller.cachedFilterOptions.selected_horizontal_group_id
        ) {
            return;
        }
        await this.filterClicked({
            optionKey: "selected_horizontal_group_id",
            optionValue: horizontalGroupId,
            reload: true,
        });
    },

    selectBudget(budget) {
        budget.selected = !budget.selected;
        this.applyFilters("budgets");
    },

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
        const cachedFilterOptions = this.controller.cachedFilterOptions;
        this.controller.reload("budgets", {
            ...cachedFilterOptions,
            budgets: [
                ...cachedFilterOptions.budgets,
                // Selected by default if we don't have any horizontal group selected
                { id: createdId, selected: !this.isHorizontalGroupSelected },
            ],
        });
    },
});
