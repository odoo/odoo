import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add(
    "website_sale.pricelist_on_login",
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
            ...tourUtils.login({
                login: 'toto',
                password: 'long_enough_password',
                redirectUrl: '/shop',
            }),
            {
                content: "Check pricelist",
                trigger: ".o_pricelist_dropdown .dropdown-toggle:contains('User Pricelist')",
            },
        ]
    }
);
