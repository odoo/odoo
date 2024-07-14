/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('payroll_tours', {
    url: "/web",
    rainbowManMessage: _t('Congratulations! You created your first contract and generated your first payslip!'),
    sequence: 80,
    steps: () => [
    {
        trigger: `.o_app[data-menu-xmlid='hr_work_entry_contract_enterprise.menu_hr_payroll_root']`,
        content: markup(_t("Click on Payroll to manage your employee's <strong>Work Entries</strong>, <strong>Contracts</strong> and <strong>Payslips</strong>.")),
        position: 'bottom',
    },
    {
        trigger: "button[data-menu-xmlid='hr_payroll.menu_hr_payroll_employees_root']",
        content: markup(_t("First, we'll create a new <strong>Contract</strong>.")),
        position: 'bottom',
    },
    {
        trigger: "a[data-menu-xmlid='hr_payroll.menu_hr_payroll_contracts_configuration']",
        content: markup(_t('Click on Employees to pick one of your <strong>Employees</strong>.')),
        position: 'right',
    },
    {
        trigger: 'td.o_many2one_avatar_employee_cell span',
        content: markup(_t("Pick an Employee to see his <strong>Contract's History</strong>.")),
        position: 'bottom',
    },
    {
        trigger: `button[name='hr_contract_view_form_new_action']`,
        content: markup(_t('Click here to create a new <strong>Contract</strong>.')),
        position: 'bottom',
    },
    {
        trigger: `input[name='name']`,
        content: markup(_t('Add a <strong>name</strong> to the contract.')),
        position: 'bottom',
    },
    {
        trigger: `div[name='structure_type_id'] .o_external_button`,
        content: markup(_t('Check the <strong>Salary Structure Type</strong>.')),
        position: 'right',
    },
    {
        trigger: '.modal-footer .o_form_button_cancel',
        content: _t('Close the window.'),
        position: 'top',
    },
    {
        trigger: `div[name='resource_calendar_id'] .o_external_button`,
        content: markup(_t('Check the <strong>Working Schedule</strong>.')),
        position: 'right',
    },
    {
        trigger: '.modal-footer .o_form_button_cancel',
        content: _t('Close the window.'),
        position: 'top',
    },
    {
        trigger: `div[name='hr_responsible_id']`,
        content: markup(_t('Select an <strong>HR Responsible</strong> for the contract.')),
        position: 'top',
    },
    {
        trigger: '.o_hr_contract_salary_information',
        content: markup(_t('Click on <strong>Salary Information</strong> to access additional fields.')),
        position: 'bottom',
    },
    {
        trigger: `.o_notebook div[name='wage']`,
        content: markup(_t('Define a <strong>Wage</strong>.')),
        position: 'bottom',
    },
    {
        trigger: `.o_form_statusbar button[data-value='open']`,
        content: markup(_t('Set the Contract as <strong><q>Running</q></strong>.')),
        position: 'bottom',
    },
    {
        trigger: `button[data-menu-xmlid='hr_work_entry_contract_enterprise.menu_hr_payroll_work_entries_root']`,
        content: markup(_t('Click on the <strong>Work Entries</strong> menu.')),
        position: 'bottom',
    },
    {
        trigger: `a[data-menu-xmlid='hr_work_entry_contract_enterprise.menu_work_entry']`,
        content: markup(_t('Check the <strong>Work Entries</strong> linked to your newly created Contract.')),
        position: 'right',
    },
    {
        trigger: '.o_gantt_cell .o_gantt_pill_wrapper',
        content: markup(_t('Work Entries are generated for each <strong>time period</strong> defined in the Working Schedule of the Contract.')),
        position: 'top',
    },
    {
        trigger: '.modal-footer button.btn-primary',
        auto: true,
    },
    {
        trigger: '.modal-footer .o_form_button_cancel',
        content: _t('Close the window.'),
        position: 'top',
    },
    {
        trigger: 'button.btn-payslip-generate',
        content: markup(_t('Click here to generate a <strong>Batch</strong> for the displayed Employees.')),
        position: 'bottom',
    },
    {
        trigger: `button[name='action_open_payslips']`,
        content: markup(_t('On the smartbutton, you can find all the <strong>Payslips</strong> included in the Batch.')),
        position: 'top',
    },
    {
        trigger: `td.o_data_cell[name='number']`,
        content: markup(_t('Click on the <strong>Payslip</strong>.')),
        position: 'bottom',
    },
    {
        trigger: `.o_hr_payroll_worked_days_input`,
        content: markup(_t('On the first tab is the amount of worked time giving you a <strong>gross amount</strong>.')),
        position: 'top',
    },
    {
        trigger: `.o_hr_payroll_salary_computation`,
        content: markup(_t('On the second tab is the computation of the rules linked to the Structure resulting in a <strong>net amount</strong>.')),
        position: 'top',
    },
    {
        trigger: `button[name='action_payslip_done']`,
        content: markup(_t('Confirm the <strong>Payslip</strong>.')),
        position: 'bottom',
    },
    {
        trigger: `a[name='employee_id']`,
        content: markup(_t("Click here to go back to the <strong>Employee's profile</strong>.")),
        position: 'right',
    },
    {
        trigger: `div[name='payslip_count']`,
        content: _t("You can access the Payslips from the Employee's Profile."),
        position: 'bottom',
    },
]});
