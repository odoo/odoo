odoo.define('hr_expense.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('hr_expense_tour', [{
    trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"], .oe_menu_toggler[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
    content: _t("Want to manage your employee expenses and receipts? <i>Start here</i>."),
    position: 'bottom',
}, {
    trigger: 'a#o_mail_test',
    content: _t("Click to try <b>submitting an expense by email</b>. You can attach a photo of the receipt to the mail."),
    position: 'right',
}, {
    trigger: '.o_expense_submit:visible',
    content: _t("<p>Once completed, you can <b>submit the expense</b> for approval.</p><p><i>Tip: from the list view, select all expenses to submit them all at once, in a single report.</i></p>"),
    extra_trigger: '.o_form_readonly',
    position: 'bottom',
}, {
    trigger: '.o_form_button_save:visible',
    extra_trigger: '.o_expense_sheet',
    content: _t("Save the report, your manager will receive a notification by email to approve it."),
    position: 'right',
}, {
    trigger: '.o_expense_sheet_approve:visible',
    content: _t("<p>Managers can validate or refuse expense reports.</p><p>If you refuse a report, explain the reason using the <i>New Message</i> button in the bottom.</p>"),
    position: 'bottom',
}, {
    trigger: '.o_expense_sheet_post:visible',
    content: _t("<p>The accountant receive approved expense reports.</p><p>He can post journal entries in one click if taxes and accounts are right.</p>"),
    position: 'bottom',
}, {
    trigger: '.o_expense_sheet_pay:visible',
    content: _t("The accountant can register a payment to reimburse the employee directly."),
    position: 'bottom',
}, {
    trigger: 'li a[data-menu-xmlid="hr_expense.menu_hr_expense_sheet_my_all"], div[data-menu-xmlid="hr_expense.menu_hr_expense_sheet_my_all"]',
    content: _t("Managers can get all reports to approve from this menu."),
    position: 'bottom',
}]);

});
