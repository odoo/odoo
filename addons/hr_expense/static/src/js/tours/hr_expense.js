odoo.define('hr_expense.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('hr_expense_tour' , {
    url: "/web"
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
    content: _t("Want to manage your expenses? It starts here."),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
    content: _t("Want to manage your expenses? It starts here."),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: '.o_form_button_save',
    content: _t("<p>Once your <b> Expense </b> is ready, you can save it.</p>"),
    position: 'bottom',
}, {
    trigger: '.o_attach_document',
    content: _t("Attach your receipt here."),
    position: 'bottom',
}, {
    trigger: '.o_expense_submit',
    extra_triggger: ".o_expense_form",
    content: _t('<p>Click on <b> Create Report </b> to create the report.</p>'),
    position: 'right',
}, {
    trigger: '.o_expense_tree input[type=checkbox]',
    content: _t('<p>Select expenses to submit them to your manager</p>'),
    position: 'bottom'
}, {
    trigger: '.o_dropdown_toggler_btn',
    extra_trigger: ".o_expense_tree",
    content: _t('<p>Click on <b> Action Create Report </b> to submit selected expenses to your manager</p>'),
    position: 'right',
},  {
    trigger: '.o_expense_sheet_submit',
    content: _t('Once your <b>Expense report</b> is ready, you can submit it to your manager and wait for the approval from your manager.'),
    position: 'bottom',
}, {
    trigger: '.o_expense_sheet_approve',
    content: _t("<p>Approve the report here.</p><p>Tip: if you refuse, don’t forget to give the reason thanks to the hereunder message tool</p>"),
    position: 'bottom',
}, {
    trigger: '.o_expense_sheet_post',
    content: _t("<p>The accountant receive approved expense reports.</p><p>He can post journal entries in one click if taxes and accounts are right.</p>"),
    position: 'bottom',
}, {
    trigger: '.o_expense_sheet_pay',
    content: _t("The accountant can register a payment to reimburse the employee directly."),
    position: 'bottom',
}, {
    trigger: 'li a[data-menu-xmlid="hr_expense.menu_hr_expense_sheet_my_all"], div[data-menu-xmlid="hr_expense.menu_hr_expense_sheet_my_all"]',
    content: _t("Managers can get all reports to approve from this menu."),
    position: 'bottom',
}]);

});
