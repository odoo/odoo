odoo.define('website.tour_reset_password', function (require) {
'use strict';

var tour = require('web_tour.tour');
require('web.dom_ready');

tour.register('website_reset_password', {
    test: true,
}, [
    {
        content: "fill new password",
        trigger: '.oe_reset_password_form input[name="password"]',
        run: "text adminadmin"
    },
    {
        content: "fill confirm password",
        trigger: '.oe_reset_password_form input[name="confirm_password"]',
        run: "text adminadmin"
    },
    {
        content: "submit reset password form",
        trigger: '.oe_reset_password_form button[type="submit"]',
    },
    {
        content: "check that we're logged in",
        trigger: '.oe_topbar_name:contains("The King")',
        run: function () {}
    },
]);
});
