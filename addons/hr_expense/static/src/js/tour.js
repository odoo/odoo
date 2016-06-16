odoo.define('hr_expense.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('hr_expense_tour', {
    'skip_enabled': true,
}, [{
    trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"], .oe_menu_toggler[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
    content: _t("Want to manage your employee expenses? Let's go to the <b>Expenses app</b>."),
    position: 'bottom',
}]);

});
