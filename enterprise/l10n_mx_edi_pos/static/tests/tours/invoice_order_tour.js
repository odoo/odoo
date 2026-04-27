import { registry } from "@web/core/registry";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";

registry.category("web_tour.tours").add("l10n_mx_edi_pos.tour_invoice_order", {
    steps: () => [
        {
            content: "Click the POS icon",
            trigger: ".o_app[data-menu-xmlid='point_of_sale.menu_point_root']",
            run: "click",
        },
        {
            content: "Open POS session from backend",
            trigger: "button[name='open_ui']",
            run: "click",
        },
        Dialog.confirm("Open Register"),
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
            content: "Customer wants an invoice",
            trigger: ".js_invoice",
            run: "click",
        },
        {
            content: "Set Usage: 'General Expenses'",
            trigger: "select[name='l10n_mx_edi_usage']",
            run: "select G03",
        },
        {
            content: "Set Invoice to Public: 'Yes'",
            trigger: "select[name='l10n_mx_edi_cfdi_to_public']",
            run: "select 1",
        },
        Dialog.confirm(),
        Chrome.endTour(),
    ],
});

registry.category("web_tour.tours").add("l10n_mx_edi_pos.tour_invoice_order_default_usage", {
    steps: () => [
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
            content: "Select a customer",
            trigger: ".set-partner",
            run: "click",
        },
        {
            content: "Select the partner 'Arturo Garcia'",
            trigger: "tr.partner-line:contains('Arturo Garcia')",
            run: "click",
        },
        {
            content: "go to Payment",
            trigger: ".pay-order-button",
            run: "click",
        },
        {
            content: "Customer wants an invoice",
            trigger: ".js_invoice",
            run: "click",
        },
        Dialog.confirm(),
        {
            content: "Option I01 should be selected",
            trigger: "div.mx_invoice:contains('Constructions')",
        },
        Chrome.endTour(),
    ],
});

registry.category("web_tour.tours").add("tour_invoice_to_general_public", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Whiteboard Pen"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Arturo Garcia"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickInvoiceButton(),
            {
                content: "Set Invoice to public: 'No'",
                trigger: "select[name='l10n_mx_edi_cfdi_to_public']",
                run: "select 0",
            },
            Dialog.confirm(),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            Dialog.is({ title: "Invalid Operation" }),
            Dialog.confirm(),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickInvoiceButton(),
            {
                content: "Set Invoice to public: 'Yes'",
                trigger: "select[name='l10n_mx_edi_cfdi_to_public']",
                run: "select 1",
            },
            Dialog.confirm(),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});
