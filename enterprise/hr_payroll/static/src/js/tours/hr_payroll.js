/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('payroll_tours', {
    url: "/odoo",
    steps: () => [
    {
        trigger: `.o_app[data-menu-xmlid='hr_work_entry_contract_enterprise.menu_hr_payroll_root']`,
        content: markup(_t("Click on Payroll to manage your employee's <strong>Work Entries</strong>, <strong>Contracts</strong> and <strong>Payslips</strong>.")),
        tooltipPosition: 'bottom',
        run: "click",
    },
    {
        trigger: "button[data-menu-xmlid='hr_payroll.menu_hr_payroll_employees_root']",
        content: markup(_t("First, we'll create a new <strong>Contract</strong>.")),
        tooltipPosition: 'bottom',
        run: "click",
    },
    {
        trigger: "a[data-menu-xmlid='hr_payroll.hr_menu_all_contracts']",
        content: markup(_t('Click on Employees to pick one of your <strong>Employees</strong>.')),
        tooltipPosition: 'right',
        run: "click",
    },
    {
        trigger: `.o_list_button_add`,
        content: markup(_t('Click here to create a new <strong>Contract</strong>.')),
        tooltipPosition: 'bottom',
        run: "click",
    },
    {
        trigger: `div[name='name'] input`,
        content: markup(_t('Add a <strong>name</strong> to the contract.')),
        tooltipPosition: 'bottom',
        run:'edit Test',
    },
    {
        trigger: ".o_field_widget[name='employee_id'] input",
        content: _t("Add a employee to your contract"),
        tooltipPosition: "right",
        run: 'click',
    },
    {
        isActive: ["auto"],
        trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
        id: 'hr_payroll_start',
        run: 'click',
    },
    {
        trigger: '.o_hr_contract_salary_information',
        content: markup(_t('Click on <strong>Salary Information</strong> to access additional fields.')),
        tooltipPosition: 'bottom',
        run: "click",
    },
    {
        trigger: `.o_notebook div[name='wage'] input`,
        content: markup(_t('Define a <strong>Wage</strong>.')),
        tooltipPosition: 'bottom',
        run: 'edit 1000',
    },
    {
        trigger: "button.o_form_button_save",
        content: "Save Contract",
        tooltipPosition: 'bottom',
        run: "click",
    },
    {
        trigger: `.o_form_statusbar button[data-value='open']`,
        content: markup(_t('Set the Contract as <strong><q>Running</q></strong>.')),
        tooltipPosition: 'bottom',
        run: "click",
    },
    {
        trigger: `button[data-menu-xmlid='hr_work_entry_contract_enterprise.menu_hr_payroll_work_entries_root']`,
        content: markup(_t('Click on the <strong>Work Entries</strong> menu.')),
        tooltipPosition: 'bottom',
        run: "click",
    },
    {
        trigger: `a[data-menu-xmlid='hr_work_entry_contract_enterprise.menu_work_entry']`,
        content: markup(_t('Check the <strong>Work Entries</strong> linked to your newly created Contract.')),
        tooltipPosition: 'right',
        run: "click",
    },
    {
        trigger: ".o_searchview .o_facet_remove",
        content: _t('Remove "Conflicting" filter'),
        run: "click",
    },
    {
        trigger: '.o_gantt_pill_wrapper',
        content: markup(_t('Work Entries are generated for each <strong>time period</strong> defined in the Working Schedule of the Contract.')),
        tooltipPosition: 'top',
        run: "click",
    },
    {
        trigger: 'button.btn-payslip-generate',
        content: markup(_t('Click here to generate a <strong>Batch</strong> for the displayed Employees.')),
        tooltipPosition: 'bottom',
        run: "click",
    },
    {
        trigger: `button[name='action_open_payslips']`,
        content: markup(_t('On the smartbutton, you can find all the <strong>Payslips</strong> included in the Batch.')),
        tooltipPosition: 'top',
        run: "click",
    },
    {
        trigger: `table.o_list_table tr.o_data_row:last .o_data_cell[name='number']`,
        content: markup(_t('Click on the <strong>Payslip</strong>.')),
        tooltipPosition: 'top',
        run: "click",
    },
    {
        trigger: `.o_hr_payroll_worked_days_input`,
        content: markup(_t('On the first tab is the amount of worked time giving you a <strong>gross amount</strong>.')),
        tooltipPosition: 'top',
        run: "click",
    },
    {
        trigger: `.o_hr_payroll_salary_computation`,
        content: markup(_t('On the second tab is the computation of the rules linked to the Structure resulting in a <strong>net amount</strong>.')),
        tooltipPosition: 'top',
        run: "click",
    },
    {
        trigger: `button[name='action_payslip_done']`,
        content: markup(_t('Confirm the <strong>Payslip</strong>.')),
        tooltipPosition: 'bottom',
        run: 'click',
    },
]});
