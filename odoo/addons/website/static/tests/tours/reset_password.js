/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_reset_password', {
    test: true,
    steps: () => [
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
        trigger: '.o_user_menu .dropdown-toggle',
        run: function () {}
    },
]});
