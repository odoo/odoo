import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add(
    "website_sale.website_sale_shop_pricelist_tour",
    {
        url: '/shop',
        steps: () => [
            {
                content: "Check pricelist",
                trigger: ".o_pricelist_dropdown .dropdown-toggle:not(:contains('User Pricelist'))",
            },
            {
                content: "Go to login page",
                trigger: "a:contains('Sign in')",
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: "Submit login",
                trigger: '.oe_login_form',
                run: function () {
                    document.querySelector('.oe_login_form input[name="login"]').value = "toto";
                    document.querySelector('.oe_login_form input[name="password"]').value = "long_enough_password";
                    document.querySelector('.oe_login_form input[name="redirect"]').value = "/shop";
                    document.querySelector('.oe_login_form').submit();
                },
                expectUnloadPage: true,
            },
            {
                content: "Check pricelist",
                trigger: ".o_pricelist_dropdown .dropdown-toggle:contains('User Pricelist')",
            },
        ]
    }
);
