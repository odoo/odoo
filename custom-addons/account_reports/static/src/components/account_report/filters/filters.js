/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { WarningDialog } from "@web/core/errors/error_dialogs";

import { DateTimeInput } from '@web/core/datetime/datetime_input';
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";

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
        this.companyService = useService("company");
        this.controller = useState(this.env.controller);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Getters
    //------------------------------------------------------------------------------------------------------------------
    get selectedFiscalPositionName() {
        switch (this.controller.options.fiscal_position) {
            case "domestic":
                return "Domestic";
            case "all":
                return "All";
            default:
                for (const fiscalPosition of this.controller.options.available_vat_fiscal_positions)
                    if (fiscalPosition.id === this.controller.options.fiscal_position)
                        return fiscalPosition.name;
        }
    }

    get selectedHorizontalGroupName() {
        for (const horizontalGroup of this.controller.options.available_horizontal_groups)
            if (horizontalGroup.id === this.controller.options.selected_horizontal_group_id)
                return horizontalGroup.name;

        return "None";
    }

    get selectedTaxUnitName() {
        if (this.controller.options.tax_unit === "company_only")
            return "Company Only";
        else
            for (const taxUnit of this.controller.options.available_tax_units)
                if (taxUnit.id === this.controller.options.tax_unit)
                    return taxUnit.name;
    }

    get selectedVariantName() {
        for (const variant of this.controller.options.available_variants)
            if (variant.id === this.controller.options.selected_variant_id)
                return variant.name;
    }

    get selectedSectionName() {
        for (const section of this.controller.options.sections)
            if (section.id === this.controller.options.selected_section_id)
                return section.name;
    }

    get selectedAccountType() {
        let selectedAccountType = this.controller.options.account_type.filter(accountType => accountType.selected);
        if (!selectedAccountType.length) { return _t("None"); }
        if (selectedAccountType.length === 4) { return _t("All"); }

        const accountTypeMappings = [
            {list: ['trade_receivable', 'non_trade_receivable'], name: _t('All Receivable')},
            {list: ['trade_payable', 'non_trade_payable'], name: _t('All Payable')},
            {list: ['trade_receivable', 'trade_payable'], name: _t('Trade Partners')},
            {list: ['non_trade_receivable', 'non_trade_payable'], name: _t('Non Trade Partners')},
        ]

        const listToDisplay = []
        for (const mapping of accountTypeMappings) {
            if (mapping.list.every(accountType => selectedAccountType.map(accountType => accountType.id).includes(accountType))) {
                listToDisplay.push(mapping.name);
                // Delete already checked id
                selectedAccountType = selectedAccountType.filter(accountType => !mapping.list.includes(accountType.id));
            }
        }

        return listToDisplay.concat(selectedAccountType.map(accountType => accountType.name)).join(', ')
    }

    get selectedAmlIrFilters() {
        const selected = [];

        for (const amlIrFilter of this.controller.options.aml_ir_filters)
            if (amlIrFilter.selected) {
                selected.push(amlIrFilter);
            }

        if (!selected.length)
            return _t("None");

        else if (selected.length === 1)
            return selected[0].name;

        else if (selected.length > 1)
            return _t("%s selected", selected.length)
    }

    //------------------------------------------------------------------------------------------------------------------
    // Helpers
    //------------------------------------------------------------------------------------------------------------------
    get hasAnalyticGroupbyFilter() {
        return Boolean(this.controller.groups.analytic_accounting) && (Boolean(this.controller.filters.show_analytic_groupby) || Boolean(this.controller.filters.show_analytic_plan_groupby));
    }

    get hasExtraOptionsFilter() {
        return "report_cash_basis" in this.controller.options || this.controller.filters.show_draft || this.controller.filters.show_all || this.controller.filters.show_unreconciled || this.controller.filters.show_hide_0_lines;
    }

    get hasFiscalPositionFilter() {
        return this.controller.options.available_vat_fiscal_positions.length > (this.controller.options.allow_domestic ? 0 : 1) && (this.controller.options.companies.length > 1);
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

    localeDateFrom(optionKey) {
        return this.dateFrom(optionKey).toLocaleString(DateTime.DATE_MED);
    }

    localeDateTo(optionKey) {
        return this.dateTo(optionKey).toLocaleString(DateTime.DATE_MED);
    }

    // Setters
    setDate(optionKey, type, date) {
        if (date)
            this.controller.options[optionKey][`date_${type}`] = date;
        else
            this.dialog.add(WarningDialog, {
                title: _t("Odoo Warning"),
                message: _t("Date cannot be empty"),
            });
    }

    setDateFrom(optionKey, dateFrom) {
        this.setDate(optionKey, 'from', dateFrom);
    }

    setDateTo(optionKey, dateTo) {
        this.setDate(optionKey, 'to', dateTo);
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
                this.updateFilter(optionKey, resIds);
            },
        };
    }

    //------------------------------------------------------------------------------------------------------------------
    // Rounding unit
    //------------------------------------------------------------------------------------------------------------------
    roundingUnitName(roundingUnit) {
        return _t("In %s", this.controller.options['rounding_unit_names'][roundingUnit]);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Generic filters
    //------------------------------------------------------------------------------------------------------------------
    async updateFilter(optionKey, optionValue) {
        await this.controller.updateOption(optionKey, optionValue, true);
    }

    async toggleFilter(optionKey) {
        await this.controller.toggleOption(optionKey, true);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Custom filters
    //------------------------------------------------------------------------------------------------------------------
    async filterJournal(journal) {
        if (journal.model === 'account.journal.group')
            this.controller.options.__journal_group_action = {
                'action': journal.selected ? "remove" : "add",
                'id': parseInt(journal.id),
            };

        journal.selected = !journal.selected;

        await this.controller.reload('journals', this.controller.options);
    }

    async filterVariant(reportId) {
        this.controller.saveSessionOptions({...this.controller.options, 'selected_variant_id': reportId, 'sections_source_id': reportId});
        this.controller.displayReport(reportId);
    }

    async filterTaxUnit(taxUnit) {
        await this.controller.updateOption('tax_unit', taxUnit.id);
        this.controller.saveSessionOptions(this.controller.options);

        // force the company to those impacted by the tax units
        this.companyService.setCompanies(taxUnit.company_ids);
    }

    async toggleHideZeroLines() {
        // Avoid calling the database when this filter is toggled; as the exact same lines would be returned; just reassign visibility.
        await this.controller.toggleOption('hide_0_lines', false);

        this.controller.saveSessionOptions(this.controller.options);
        this.controller.setLineVisibility(this.controller.lines);
    }

    async filterRoundingUnit(rounding) {
        await this.controller.updateOption('rounding_unit', rounding, false);

        this.controller.saveSessionOptions(this.controller.options);

        this.controller.lines = await this.controller.orm.call(
            "account.report",
            "format_column_values",
            [
                this.controller.options,
                this.controller.lines,
            ],
        );
    }
}
