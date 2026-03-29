/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_purchase_user_access_flow", {
    steps: () => [
        {
            content: "The bill matching button must not be accessible to the purchase user.",
            trigger: ".o-form-buttonbox:not(:has(button[name='action_bill_matching']))",
        },
        {
            content: "The purchase user should be able to access the relevant bills.",
            trigger: "button[name='action_view_invoice']",
            run: "click",
        },
        {
            content: "Return to the purchase order.",
            trigger: "button[name='action_view_source_purchase_orders']",
            run: "click",
        },
        {
            content: "The purchase user should be able to access the order's pickings.",
            trigger: "button[name='action_view_picking']",
            run: "click",
        },
    ],
})
