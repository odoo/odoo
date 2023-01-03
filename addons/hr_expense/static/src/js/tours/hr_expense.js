odoo.define('hr_expense.tour', function(require) {
"use strict";

const {_t} = require('web.core');
const {Markup} = require('web.utils');
var tour = require('web_tour.tour');

tour.register('hr_expense_tour' , {
    url: "/web",
    rainbowManMessage: _t("There you go - expense management in a nutshell!"),
}, [tour.stepUtils.showAppsMenuItem(), {
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
    extra_trigger: '.o_expense_form',
    content: _t("Enter a name then choose a category and configure the amount of your expense."),
    position: 'bottom',
}, {
    trigger: '.o_form_status_indicator_dirty .o_form_button_save',
    extra_trigger: '.o_expense_form',
    content: Markup(_t("Ready? You can save it manually or discard modifications from here. You don't <em>need to save</em> - Odoo will save eveyrthing for you when you navigate.")),
    position: 'bottom',
}, ...tour.stepUtils.statusbarButtonsSteps(_t("Attach Receipt"), _t("Attach a receipt - usually an image or a PDF file.")),
...tour.stepUtils.statusbarButtonsSteps(_t("Create Report"), _t("Create a report to submit one or more expenses to your manager.")),
...tour.stepUtils.statusbarButtonsSteps(_t("Submit to Manager"), Markup(_t('Once your <b>Expense Report</b> is ready, you can submit it to your manager and wait for approval.'))),
...tour.stepUtils.goBackBreadcrumbsMobile(
    _t("Use the breadcrumbs to go back to the list of expenses."),
    undefined,
    ".o_expense_form",
),
{
    trigger: '.breadcrumb > li.breadcrumb-item:first',
    extra_triggger: ".o_expense_form",
    content: _t("Let's go back to your expenses."),
    position: 'bottom',
    mobile: false,
}, {
    trigger: '.o_expense_container',
    content: _t("The status of all your current expenses is visible from here."),
    position: 'bottom',
},
tour.stepUtils.openBuggerMenu(),
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
...tour.stepUtils.statusbarButtonsSteps(_t("Approve"), _t("Managers can approve the report here, then an accountant can post the accounting entries.")),
]);

});
