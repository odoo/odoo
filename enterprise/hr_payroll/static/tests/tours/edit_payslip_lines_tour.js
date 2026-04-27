/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('hr_payroll_edit_payslip_lines_tour', {
    url: '/odoo',
    steps: () => [
    stepUtils.showAppsMenuItem(),
    {
        content: "Open Payroll app",
        trigger: '.o_app[data-menu-xmlid="hr_work_entry_contract_enterprise.menu_hr_payroll_root"]',
        run: "click",
    },
    {
        content: "Click Payslips",
        trigger: '[data-menu-xmlid="hr_payroll.menu_hr_payroll_payslips"]',
        run: "click",
    },
    {
        content: "Click All Payroll",
        trigger: '[data-menu-xmlid="hr_payroll.menu_hr_payroll_employee_payslips"]',
        run: "click",
    },
    {
        content: 'Remove "Batch" filter',
        trigger: ".o_searchview .o_facet_remove",
        run: "click",
    },
    {
        content: "Click on payslip",
        trigger: '.o_data_row td:contains("Richard")',
        run: "click",
    },
    {
        content: "Wait for the page to be loaded",
        trigger: ".o_form_view_container .o_control_panel .o_cp_action_menus .dropdown-toggle",
    },
    {
        trigger: ".o_form_sheet",
    },
    {
        content: "Click on action",
        trigger: ".o_control_panel .o_cp_action_menus .dropdown-toggle",
        run: "click",
    },
    {
        content: "Click on Edit Payslip Lines",
        trigger: 'span:contains("Edit Payslip Lines")',
        run: "click",
    },
    {
        content: "Click payslip line",
        trigger: '.o_field_widget[name=line_ids] td.o_data_cell:contains("1,234.00")',
        run: "click",
    },
    {
        content: "Modify payslip line",
        trigger: ".o_field_widget[name=line_ids] .o_field_widget[name=amount] input",
        run: "edit 4321.00",
    },
    {
        content: "Click out",
        trigger: 'span:contains("Tip")',
        run: "click",
    },
    {
        content: "Check that the line is indeed modified",
        trigger: '.o_field_widget[name=line_ids] td.o_data_cell:contains("4,321.00")',
    },
    {
        trigger: ".modal-header:contains(Odoo)",
    },
    {
        content: "Validate changes",
        trigger: ".modal-footer .btn-primary:contains('Validate Edition')",
        run: "click",
    },
    {
        content: "Click on Salary Computation page",
        trigger: 'a:contains("Salary Computation")',
        run: "click",
    },
    {
        content: "Check that payslip line is indeed modofied",
        trigger: '.o_field_widget[name=line_ids] td.o_data_cell:contains("4,321.00")',
    },
]});
