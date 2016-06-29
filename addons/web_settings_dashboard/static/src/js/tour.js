odoo.define('web_settings_dashboard.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('web_settings_dashboard_tour', {
    'skip_enabled': true,
}, [{
    trigger: '.o_app[data-menu-xmlid="base.menu_administration"], .oe_menu_toggler[data-menu-xmlid="base.menu_administration"]',
    content: _t("Configuration options are available in the Settings app."),
    position: "bottom"
}, {
    trigger: '.o_web_settings_dashboard_invitation_form textarea[id="user_emails"]',
    content: _t("<b>Invite collegues</b> via email.<br/><i>Enter one email per line.</i>"),
    position: "bottom"
}]);

});