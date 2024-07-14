/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";

registry.category("web_tour.tours").add("l10n_mx_edi_pos.tour_invoice_previous_order", {
    test: true,
    steps: () => [
        {
            content: "Click the POS icon",
            trigger: ".o_app[data-menu-xmlid='point_of_sale.menu_point_root']",
        },
        {
            content: "Open POS session from backend",
            trigger: "button[name='open_ui']",
        },
        ...ProductScreen.confirmOpeningPopup(),
        {
            content: "Select a product",
            trigger: "div.product-content:contains('product_mx')",
        },
        {
            content: "go to Payment",
            trigger: ".pay-order-button",
        },
        {
            content: "Select payment method",
            trigger: "div.button.paymentmethod",
        },
        {
            content: "Validate",
            trigger: "div.button.next.validation",
        },
        {
            content: "click on New Order",
            trigger: "div button:contains('New Order')",
        },
        {
            content: "Click on the burger menu",
            trigger: "div.menu-button",
        },
        {
            content: "Check the previous Order",
            trigger: "li.ticket-button:contains('Orders')",
        },
        {
            content: "Select dropdown",
            trigger: "div.filter",
        },
        {
            content: "Select 'Paid Orders'",
            trigger: "li:contains('Paid')",
        },
        {
            content: "Pick the first order in the list",
            trigger: "div.order-row:contains('Paid'):first",
        },
        {
            content: "Ask an invoice for this order",
            trigger: "button.control-button:contains('Invoice')",
        },
        {
            content: "Do you want to select a customer ? Yes",
            trigger: "div.button.confirm:contains('Ok')",
        },
        {
            content: "Select the partner 'Arturo Garcia'",
            trigger: "tr.partner-line:contains('Arturo Garcia')",
        },
        {
            content: "Set Usage: 'General Expenses'",
            trigger: "select[name='l10n_mx_edi_usage']",
            run: "text G03",
        },
        {
            content: "Set Invoice to Public: 'Yes'",
            trigger: "select[name='l10n_mx_edi_cfdi_to_public']",
            run: "text 1",
        },
        {
            content: "Confirm and close the popup",
            trigger: ".button.confirm",
        },
        {
            content: "The 'Invoice' button should have now turned to 'Reprint Invoice'",
            trigger: "span:contains('Reprint Invoice')",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("l10n_mx_edi_pos.tour_invoice_previous_order_default_usage", {
    test: true,
    steps: () => [
        {
            content: "Click the POS icon",
            trigger: ".o_app[data-menu-xmlid='point_of_sale.menu_point_root']",
        },
        {
            content: "Open POS session from backend",
            trigger: "button[name='open_ui']",
        },
        ...ProductScreen.confirmOpeningPopup(),
        {
            content: "Select a product",
            trigger: "div.product-content:contains('product_mx')",
        },
        {
            content: "go to Payment",
            trigger: ".pay-order-button",
        },
        {
            content: "Select payment method",
            trigger: "div.button.paymentmethod",
        },
        {
            content: "Validate",
            trigger: "div.button.next.validation",
        },
        {
            content: "click on New Order",
            trigger: "div button:contains('New Order')",
        },
        {
            content: "Click on the burger menu",
            trigger: "div.menu-button",
        },
        {
            content: "Check the previous Order",
            trigger: "li.ticket-button:contains('Orders')",
        },
        {
            content: "Select dropdown",
            trigger: "div.filter",
        },
        {
            content: "Select 'Paid Orders'",
            trigger: "li:contains('Paid')",
        },
        {
            content: "Pick the first order in the list",
            trigger: "div.order-row:contains('Paid'):first",
        },
        {
            content: "Ask an invoice for this order",
            trigger: "button.control-button:contains('Invoice')",
        },
        {
            content: "Do you want to select a customer ? Yes",
            trigger: "div.button.confirm:contains('Ok')",
        },
        {
            content: "Select the partner 'Arturo Garcia'",
            trigger: "tr.partner-line:contains('Arturo Garcia')",
        },
        {
            content: "Set Invoice to Public: 'Yes'",
            trigger: "select[name='l10n_mx_edi_cfdi_to_public']",
            run: "text 1",
        },
        {
            content: "Confirm and close the popup",
            trigger: ".button.confirm",
        },
        {
            content: "The 'Invoice' button should have now turned to 'Reprint Invoice'",
            trigger: "span:contains('Reprint Invoice')",
            isCheck: true,
        },
    ],
});
