import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";

registry.category("web_tour.tours").add("l10n_mx_edi_pos.tour_invoice_previous_order", {
    steps: () =>
        [
            {
                content: "Click the POS icon",
                trigger: ".o_app[data-menu-xmlid='point_of_sale.menu_point_root']",
                run: "click",
            },
            {
                content: "Open POS session from backend",
                trigger: "button[name='open_ui']",
                run: "click",
                expectUnloadPage: true,
            },
            {
                content: "Open Register",
                trigger: ".modal .modal-footer .btn-primary:contains(open register)",
                run: "click",
            },
            {
                content: "Select a product",
                trigger: "div.product-content:contains('product_mx')",
                run: "click",
            },
            {
                content: "go to Payment",
                trigger: ".pay-order-button",
                run: "click",
            },
            {
                content: "Select payment method",
                trigger: "div.button.paymentmethod",
                run: "click",
            },
            ...PaymentScreen.clickValidate(),
            {
                content: "click on New Order",
                trigger: "div button:contains('New Order')",
                run: "click",
            },
            Chrome.clickMenuOption("Orders"),
            {
                content: "Select dropdown",
                trigger: "div.filter",
                run: "click",
            },
            {
                content: "Select 'Paid Orders'",
                trigger: "li:contains('Paid')",
                run: "click",
            },
            {
                content: "Pick the first order in the list",
                trigger: "div.order-row:contains('Paid'):first",
                run: "click",
            },
            {
                content: "Ask an invoice for this order",
                trigger: ".control-buttons button:contains('Invoice')",
                run: "click",
            },
            Dialog.confirm(),
            {
                content: "Select the partner 'Arturo Garcia'",
                trigger: "tr.partner-line:contains('Arturo Garcia')",
                run: "click",
            },
            {
                content: "Set Usage: 'General Expenses'",
                trigger: "select[name='l10n_mx_edi_usage']",
                run: "select G03",
            },
            {
                content: "Set Invoice to Public: 'No'",
                trigger: "select[name='l10n_mx_edi_cfdi_to_public']",
                run: "select 0",
            },
            {
                trigger: ".modal button:contains(ok)",
                run: "click",
            },
            {
                content: "The 'Invoice' button should have now turned to 'Reprint Invoice'",
                trigger: "span:contains('Reprint Invoice')",
            },
        ].flat(),
});

registry
    .category("web_tour.tours")
    .add("l10n_mx_edi_pos.tour_invoice_previous_order_default_usage", {
        steps: () =>
            [
                {
                    content: "Click the POS icon",
                    trigger: ".o_app[data-menu-xmlid='point_of_sale.menu_point_root']",
                    run: "click",
                },
                {
                    content: "Open POS session from backend",
                    trigger: "button[name='open_ui']",
                    run: "click",
                    expectUnloadPage: true,
                },
                {
                    content: "Open Register",
                    trigger: ".modal .modal-footer .btn-primary:contains(open register)",
                    run: "click",
                },
                {
                    content: "Select a product",
                    trigger: "div.product-content:contains('product_mx')",
                    run: "click",
                },
                {
                    content: "go to Payment",
                    trigger: ".pay-order-button",
                    run: "click",
                },
                {
                    content: "Select payment method",
                    trigger: "div.button.paymentmethod",
                    run: "click",
                },
                ...PaymentScreen.clickValidate(),
                {
                    content: "click on New Order",
                    trigger: "div button:contains('New Order')",
                    run: "click",
                },
                Chrome.clickMenuOption("Orders"),
                {
                    content: "Select dropdown",
                    trigger: "div.filter",
                    run: "click",
                },
                {
                    content: "Select 'Paid Orders'",
                    trigger: "li:contains('Paid')",
                    run: "click",
                },
                {
                    content: "Pick the first order in the list",
                    trigger: "div.order-row:contains('Paid'):first",
                    run: "click",
                },
                {
                    content: "Ask an invoice for this order",
                    trigger: "button.control-button:contains('Invoice')",
                    run: "click",
                },
                Dialog.confirm(),
                {
                    content: "Select the partner 'Arturo Garcia'",
                    trigger: "tr.partner-line:contains('Arturo Garcia')",
                    run: "click",
                },
                {
                    content: "Set Invoice to Public: 'Yes'",
                    trigger: "select[name='l10n_mx_edi_cfdi_to_public']",
                    run: "select 1",
                },
                {
                    trigger: ".modal .modal-footer .btn-primary",
                    run: "click",
                },
                {
                    content: "The 'Invoice' button should have now turned to 'Reprint Invoice'",
                    trigger: "span:contains('Reprint Invoice')",
                },
            ].flat(),
    });
