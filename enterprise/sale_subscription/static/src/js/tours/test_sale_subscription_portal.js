/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_sale_subscription_portal", {
    steps: () => [
        {
            content: "Wait for the whole page to load",
            trigger: "#chatterRoot:shadow .o-mail-Chatter",
        },
        {
            content: "Check that Pay button is enabled",
            trigger: ".o_payment_form button[name='o_payment_submit_button']:not([disabled])",
        },
    ],
});

registry.category("web_tour.tours").add("test_sale_subscription_portal_payment", {
    steps: () => [
        {
            content: "Wait for the whole page to load",
            trigger: "#chatterRoot:shadow .o-mail-Chatter",
        },
        {
            content: "Check that payment_message section is  not rendered",
            trigger: ":not(:contains(section#payment_message))",
        },
    ],
});

registry.category("web_tour.tours").add("test_optional_products_portal", {
    steps: () => [
        {
            content: "Wait for the whole page to load",
            trigger: "#chatterRoot:shadow .o-mail-Chatter",
        },
        {
            content: "Check optional product are shown",
            trigger: 'div[id="content"] h3[id="quote_3"]',
        },
    ],
});
