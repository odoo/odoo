/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('sale_subscription_product_variants', {
    test: true,
    steps: () => [
        {
            content: "Trigger first period (Month)",
            trigger: "input[title='Monthly']",
            run: "click",
        },
        {
            content: "Check ",
            trigger: ".o_subscription_unit:contains('per month')",
            run: function () {},
        },
        {
            content: "Trigger second period (2 Months)",
            trigger: "input[title='2 Months']",
            run: "click",
        },
        {
            content: "Check ",
            trigger: ".o_subscription_unit:contains('per 2 month')",
            run: function () {},
        },
        {
            content: "Trigger third period (Yearly)",
            trigger: "input[title='Yearly']",
            run: "click",
        },
        {
            content: "Check ",
            trigger: ".o_subscription_unit:contains('per year')",
            run: function () {},
        },
    ]
});
