/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
<<<<<<< saas-17.2
import * as PartnerList from "@point_of_sale/../tests/tours/helpers/PartnerListTourMethods";
||||||| 6d0baa2194720188fe50e2a4a89ce6018c90c718
import * as PartnerListScreen from "@point_of_sale/../tests/tours/helpers/PartnerListScreenTourMethods";
=======
import * as PartnerListScreen from "@point_of_sale/../tests/tours/helpers/PartnerListScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as Utils from "@point_of_sale/../tests/tours/helpers/utils";
>>>>>>> 92b18a1a5fcdf0214938683abf8566883af5e156
import { registry } from "@web/core/registry";
import { checkSimplifiedInvoiceNumber, pay } from "./helpers/receipt_helpers";

const SIMPLIFIED_INVOICE_LIMIT = 1000;

registry.category("web_tour.tours").add("spanish_pos_tour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.addOrderline("Desk Pad", "1"),
            pay(),
            checkSimplifiedInvoiceNumber("0001"),
            ReceiptScreen.clickNextOrder(),

            ProductScreen.addOrderline("Desk Pad", "1", SIMPLIFIED_INVOICE_LIMIT - 1),
            pay(),
            checkSimplifiedInvoiceNumber("0002"),
            ReceiptScreen.clickNextOrder(),

            ProductScreen.addOrderline("Desk Pad", "1", SIMPLIFIED_INVOICE_LIMIT + 1),
            pay(),
            Dialog.confirm(),

            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            // verify that the pos requires the selection of a partner
            Dialog.confirm(),
            PartnerList.clickPartner(""),

            PaymentScreen.isInvoiceOptionSelected(),
            PaymentScreen.clickValidate(),
            {
                content:
                    "verify that the simplified invoice number does not appear on the receipt, because this order is invoiced, so it does not have a simplified invoice number",
                trigger: ".receipt-screen:not(:has(.simplified-invoice-number))",
                isCheck: true,
            },
            ReceiptScreen.clickNextOrder(),

<<<<<<< saas-17.2
            ProductScreen.addOrderline("Desk Pad", "1"),
            pay(),
            checkSimplifiedInvoiceNumber("0003"),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Customer Account"),
            PaymentScreen.clickValidate(),
            Dialog.is({ title: "Customer Required" }),
        ].flat(),
||||||| 6d0baa2194720188fe50e2a4a89ce6018c90c718
        ...PaymentScreen.isInvoiceOptionSelected(),
        ...PaymentScreen.clickValidate(),
        {
            content:
                "verify that the simplified invoice number does not appear on the receipt, because this order is invoiced, so it does not have a simplified invoice number",
            trigger: ".receipt-screen:not(:has(.simplified-invoice-number))",
            isCheck: true,
        },
        ...ReceiptScreen.clickNextOrder(),

        ...ProductScreen.addOrderline("Desk Pad", "1"),
        ...pay(),
        ...checkSimplifiedInvoiceNumber("0003"),

        ...ReceiptScreen.clickNextOrder(),
        ...ProductScreen.addOrderline("Desk Pad", "1"),
        ...ProductScreen.clickPayButton(),
        ...PaymentScreen.clickPaymentMethod("Customer Account"),
        ...PaymentScreen.clickValidate(),
        {
            content: "verify that the pos requires the selection of a partner",
            trigger: `div.popup.popup-confirm .modal-header:contains('Customer Required')`,
        },

    ],
=======
        ...PaymentScreen.isInvoiceOptionSelected(),
        ...PaymentScreen.clickValidate(),
        {
            content:
                "verify that the simplified invoice number does not appear on the receipt, because this order is invoiced, so it does not have a simplified invoice number",
            trigger: ".receipt-screen:not(:has(.simplified-invoice-number))",
            isCheck: true,
        },
        ...ReceiptScreen.clickNextOrder(),

        ...ProductScreen.addOrderline("Desk Pad", "1"),
        ...pay(),
        ...checkSimplifiedInvoiceNumber("0003"),

        ...ReceiptScreen.clickNextOrder(),
        ...ProductScreen.addOrderline("Desk Pad", "1"),
        ...ProductScreen.clickPayButton(),
        ...PaymentScreen.clickPaymentMethod("Customer Account"),
        ...PaymentScreen.clickValidate(),
        {
            content: "verify that the pos requires the selection of a partner",
            trigger: `div.popup.popup-confirm .modal-header:contains('Customer Required')`,
        },
    ],
>>>>>>> 92b18a1a5fcdf0214938683abf8566883af5e156
});

registry.category("web_tour.tours").add("l10n_es_pos_settle_account_due", {
    test: true,
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickPartnerButton(),
            PartnerListScreen.clickPartnerDetailsButton("Partner Test 1"),
            {
                trigger: `.button:contains("Settle due accounts")`,
            },
            Utils.selectButton("Bank"),
            PaymentScreen.clickValidate(),
            Chrome.confirmPopup(),
            ReceiptScreen.isShown(),
        ].flat(),
});
