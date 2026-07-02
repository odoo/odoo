import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('hr_expense_tour' , {
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
    content: markup(_t("<b>Wasting time recording your receipts?</b> Let’s try a better way.")),
    tooltipPosition: 'right',
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
    content: markup(_t("<b>Wasting time recording your receipts?</b> Let’s try a better way.")),
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_button_upload_expense",
},
{
    isActive: ["desktop"],
    trigger: '.o_list_button_add',
    content: _t("It all begins here - let's go!"),
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".o_button_upload_expense",
},
{
    isActive: ["mobile"],
    trigger: '.o-kanban-button-new',
    content: _t("It all begins here - let's go!"),
    run: "click",
},
{
    trigger: '.o_hr_expense_form_view .o_field_widget[name="employee_id"] input',
    content: _t("Click here to create your employee profile."),
    run: "click",
},
{
    trigger: '.o_m2o_dropdown_option_create_edit',
    content: _t("Create and edit a new employee profile."),
    run: "click",
},
{
    trigger: '.o_dialog .o_field_widget[name="name"] input',
    content: _t("Enter your name to create your employee profile."),
    run: "edit My Employee",
},
{
    trigger: '.o_dialog .o_notebook .nav-link:contains("Settings")',
    content: _t("Go to the Settings tab to configure the expense approver."),
    run: "click",
},
{
    trigger: '.o_dialog .o_field_widget[name="expense_manager_id"] input',
    content: _t("Set an expense approver for this employee."),
    run: "edit Administrator",
},
{
    trigger: '.o_dialog .o_field_widget[name="expense_manager_id"] .dropdown-item:contains("Administrator")',
    content: _t("Select the expense approver."),
    run: "click",
},
{
    trigger: '.o_dialog .o_form_button_save',
    content: _t("Save the employee profile."),
    run: "click",
},
{
    trigger: '.o_hr_expense_form_view .o_field_widget[name="product_id"] input',
    content: _t("Enter a name then choose a product and configure the amount of your expense."),
    run: "edit Meals",
},
{
    trigger: '.o_field_widget[name="product_id"] .dropdown-item:contains("Meals")',
    run: "click",
},
{
    trigger: '.o_hr_expense_form_view .o_field_widget[name="total_amount_currency"] input',
    content: _t("Enter the total amount of the expense."),
    run: "edit 50",
},
{
    trigger: '.o_form_status_indicator .o_form_button_save',
    content: markup(_t("Ready? You can save it manually or discard modifications from here. You don't <em>need to save</em> - Odoo will save eveyrthing for you when you navigate.")),
    run: "click",
}, ...stepUtils.statusbarButtonsSteps(_t("Attach Receipt"), _t("Attach a receipt - usually an image or a PDF file.")),
...stepUtils.statusbarButtonsSteps(_t("Submit"), markup(_t('Once your <b>Expense</b> is ready, you can submit it to your manager and wait for approval.'))),
{
    isActive: ["mobile"],
    trigger: ".o_hr_expense_form_view",
},
{
    isActive: ["mobile"],
    trigger: ".o_back_button",
    content:  _t("Use the breadcrumbs to go back to the list of expenses."),
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: '.breadcrumb > li.breadcrumb-item:first',
    content: _t("Let's go back to your expenses."),
    run: "click",
}, {
    trigger: '.o_expense_container',
    content: _t("The status of all your current expenses is visible from here."),
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".o_mobile_menu_toggle",
    content: _t("Open burger menu."),
    run: "click",
},
{
    trigger: ".o_main_navbar",
},
{
    trigger: "[data-menu-xmlid='hr_expense.menu_hr_expense_reports']",
    content: _t("Let's check out where you can manage all your employees expenses"),
    run: "click",
},
{
    trigger: "[data-menu-xmlid='hr_expense.menu_hr_expense_all_expenses']",
    content: _t("Click on all expenses"),
    run: "click",
},
{
    trigger: ".o_graph_canvas_container",
},
{
    isActive: ["desktop"],
    trigger: '.o_cp_switch_buttons .o_list',
    content: _t("Switch to the list view."),
    run: "click",
},
{
    trigger: '.o_cp_switch_buttons .o_list.active',
},
{
    isActive: ["desktop"],
    trigger: '.o_list_renderer .o_data_row:first .o_many2one_avatar_employee_cell',
    content: _t('Managers can inspect all expenses from here.'),
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: '.o_kanban_renderer .o_kanban_record',
    content: _t('Managers can inspect all expenses from here.'),
    run: "click",
},
...stepUtils.statusbarButtonsSteps(_t("Approve"), _t("Managers can approve the expense here, then an accountant can post the accounting entries.")),
]});
