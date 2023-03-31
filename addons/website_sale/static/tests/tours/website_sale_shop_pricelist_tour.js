/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add(
    "website_sale.website_sale_shop_pricelist_tour",
    {
        test: true,
        url: '/shop',
        steps: () => [
            {
                content: "Check pricelist",
                trigger: ".o_pricelist_dropdown .dropdown-toggle:not(:contains('User Pricelist'))",
                run: function() {} // Check
            },
            {
                content: "Go to login page",
                trigger: ".btn:contains('Sign in')"
            },
            {
                content: "Submit login",
                trigger: '.oe_login_form',
                run: function () {
                    $('.oe_login_form input[name="login"]').val("toto");
                    $('.oe_login_form input[name="password"]').val("long_enough_password");
                    $('.oe_login_form input[name="redirect"]').val("/shop");
                    $('.oe_login_form').submit();
                }
            },
            {
                content: "Check pricelist",
                trigger: ".o_pricelist_dropdown .dropdown-toggle:contains('User Pricelist')",
                run: function() {} // Check
            },
        ]
    }
);
