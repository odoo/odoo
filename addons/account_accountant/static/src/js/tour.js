odoo.define('account_accountant.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('account_accountant_tour', {
    'skip_enabled': true,
}, [{
    trigger: '.o_app[data-menu-xmlid="account.menu_finance"], .oe_menu_toggler[data-menu-xmlid="account.menu_finance"]',
    content: _t('Ready to discover your new favorite <b>accounting app</b>? Get started by clicking here.'),
    position: 'bottom',
}, {
    trigger: ".o_invoice_new",
    extra_trigger: '.o_account_kanban',
    content:  _t("Let\'s start with a new customer invoice."),
    position: "bottom"
}, {
    trigger: ".breadcrumb li:not(.active):last",
    extra_trigger: "[data-id='open'].btn-primary, [data-id='open'].oe_active",
    content:  _t("Use the path to quickly click back to <b>previous screens</b>, without reloading the page."),
    position: "bottom"
}, {
    trigger: 'li a[data-menu-xmlid="account.menu_finance_reports"], div[data-menu-xmlid="account.menu_finance_reports"]',
    content: _t("Your reports are available in real time. <i>No need to close a fiscal year to get a Profit &amp; Loss statement or view the Balance Sheet.</i>"),
    position: "bottom"
}]);

});
