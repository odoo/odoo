/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('account_invoice_create', {
    test: true,
    url: "/web",
    steps: () => [
        {
            trigger: '.o_app:contains("Accounting")',
            content: 'Click the Accounting app',
            run: 'click',
        },
        {
            content: "Go to Customer Invoices",
            trigger: 'span:contains("Customer")',
            run: 'click',
        },
        {
            content: "Go to Invoices",
            trigger: 'a:contains("Invoices")',
            run: 'click',
        },
        {
            extra_trigger: '.o_breadcrumb .text-truncate:contains("Invoices")',
            content: "Create new bill",
            trigger: '.o_control_panel_main_buttons .d-none .o_list_button_add',
            run: 'click',
        },
        {
            content: 'Ensure Preview button is not visible',
            trigger: '.o_statusbar_buttons:not(:has(button[name="preview_invoice"]))',
            run: () => {},
        },
    ],
});
