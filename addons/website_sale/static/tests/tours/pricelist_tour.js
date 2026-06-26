import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale.pricelist_on_login", {
    steps: () => [
        {
            content: "Check public user can't select user specific pricelist",
            trigger:
                `header div[name="pricelist_selector"]:not(:has(.dropdown-item:contains("User Pricelist")))`,
        },
        {
            content: "Go to login page",
            trigger: "a:contains('Sign in')",
            run: "click",
            expectUnloadPage: true,
        },
        ...tourUtils.login({
            login: "toto",
            password: "long_enough_password",
            redirectUrl: "/shop",
        }),
        {
            content: "Check user specific pricelist is active by default once logged in",
            trigger: `header div[name="pricelist_selector"] .dropdown-toggle:contains("User Pricelist")`,
        },
    ],
});
