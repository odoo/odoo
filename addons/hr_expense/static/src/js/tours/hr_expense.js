/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('hr_expense_tour' , {
    url: "/web",
    rainbowManMessage: _t("There you go - expense management in a nutshell!"),
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
    content: _t("Wasting time recording your receipts? Let’s try a better way."),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
    content: _t("Wasting time recording your receipts? Let’s try a better way."),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: '.o_list_button_add',
    extra_trigger: '.o_button_upload_expense',
    content: _t("It all begins here - let's go!"),
    position: 'bottom',
    mobile: false,
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_button_upload_expense',
    content: _t("It all begins here - let's go!"),
    position: 'bottom',
    mobile: true,
}, {
    trigger: '.o_field_widget[name="product_id"] .o_input_dropdown',
    extra_trigger: '.o_hr_expense_form_view_view',
    content: _t("Enter a name then choose a category and configure the amount of your expense."),
    position: 'bottom',
}, {
    trigger: '.o_form_status_indicator_dirty .o_form_button_save',
    extra_trigger: '.o_hr_expense_form_view_view',
    content: markup(_t("Ready? You can save it manually or discard modifications from here. You don't <em>need to save</em> - Odoo will save eveyrthing for you when you navigate.")),
    position: 'bottom',
}, ...stepUtils.statusbarButtonsSteps(_t("Attach Receipt"), _t("Attach a receipt - usually an image or a PDF file.")),
...stepUtils.statusbarButtonsSteps(_t("Create Report"), _t("Create a report to submit one or more expenses to your manager.")),
...stepUtils.statusbarButtonsSteps(_t("Submit to Manager"), markup(_t('Once your <b>Expense Report</b> is ready, you can submit it to your manager and wait for approval.'))),
...stepUtils.goBackBreadcrumbsMobile(
    _t("Use the breadcrumbs to go back to the list of expenses."),
    undefined,
    ".o_hr_expense_form_view_view",
),
{
    trigger: '.breadcrumb > li.breadcrumb-item:first',
    extra_triggger: ".o_hr_expense_form_view_view",
    content: _t("Let's go back to your expenses."),
    position: 'bottom',
    mobile: false,
}, {
    trigger: '.o_expense_container',
    content: _t("The status of all your current expenses is visible from here."),
    position: 'bottom',
},
stepUtils.openBurgerMenu(),
{
    trigger: "[data-menu-xmlid='hr_expense.menu_hr_expense_report']",
    extra_trigger: '.o_main_navbar',
    content: _t("Let's check out where you can manage all your employees expenses"),
    position: "bottom"
}, {
    trigger: '.o_list_renderer tbody tr[data-id]',
    content: _t('Managers can inspect all expenses from here.'),
    position: 'bottom',
    mobile: false,
}, {
    trigger: '.o_kanban_renderer .oe_kanban_card',
    content: _t('Managers can inspect all expenses from here.'),
    position: 'bottom',
    mobile: true,
},
...stepUtils.statusbarButtonsSteps(_t("Approve"), _t("Managers can approve the report here, then an accountant can post the accounting entries.")),
]});
