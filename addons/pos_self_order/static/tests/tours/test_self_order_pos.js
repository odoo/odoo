/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_table_stand_number_exported", {
    test: true,
    steps: () =>
        [
            {
                trigger: '.opening-cash-control .button:contains("Open session")'
            },
            {
                content: "Click on the menu button",
                trigger: ".menu-button",
            },
            {
                content: "Click Orders dropdown item",
                trigger: '.dropdown-item.with-badge.py-2:contains("Orders")',
            },
            {
                content: "Select order",
                trigger: '.order-row:contains("12345678901234")',
                run: 'dblclick',            
            },
            {
                content: "Click product Whiteboard Pen",
                trigger: '.product-name:contains("Whiteboard Pen")',
            },
            {
                content: "click pay button",
                trigger: ".product-screen .pay-order-button",
            },
            {
                content: `click cash payment method`,
                trigger: `.paymentmethods .button.paymentmethod:contains("Cash")`,
            },
            {
                content: "validate payment",
                trigger: `.payment-screen .button.next.highlight`,
            },
        ].flat(),
});
