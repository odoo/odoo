import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import { registry } from "@web/core/registry";
import { checkSimplifiedInvoiceNumber, pay } from "./utils/receipt_util";

const SIMPLIFIED_INVOICE_LIMIT = 1000;

registry.category("web_tour.tours").add("spanish_pos_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Desk Pad", "1"),
            pay(),
            FeedbackScreen.isShown(),
            checkSimplifiedInvoiceNumber("0001"),
            FeedbackScreen.clickNextOrder(),

            ProductScreen.addOrderline("Desk Pad", "1", SIMPLIFIED_INVOICE_LIMIT - 1),
            pay(),
            FeedbackScreen.isShown(),
            checkSimplifiedInvoiceNumber("0002"),
            FeedbackScreen.clickNextOrder(),

            ProductScreen.addOrderline("Desk Pad", "1", SIMPLIFIED_INVOICE_LIMIT + 1),
            pay(),
            Dialog.confirm(),

            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.isInvoiceOptionSelected(),
            PaymentScreen.clickValidate(),
            // verify that the pos requires the selection of a partner
            Dialog.confirm(),
            PartnerList.clickPartner(""),

            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                cssRules: [
                    {
                        css: ".simplified-invoice-number",
                        negation: true,
                    },
                    {
                        css: "pos-receipt-container div",
                        text: "Badajoz",
                    },
                ],
            }),
            FeedbackScreen.clickNextOrder(),

            ProductScreen.addOrderline("Desk Pad", "1"),
            pay(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                cssRules: [
                    {
                        css: ".simplified-invoice-number",
                        text: "0003",
                    },
                    {
                        css: "pos-receipt-container div",
                        text: "Badajoz",
                    },
                ],
            }),
            FeedbackScreen.clickNextOrder(),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Customer Account"),
            PaymentScreen.clickValidate(),
            Dialog.is({ title: "Customer Required" }),
        ].flat(),
});

registry.category("web_tour.tours").add("l10n_es_pos_settle_account_due", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.settleCustomerAccount("Partner Test 1", "10.0", "TSJ/", "/00001", true),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Chrome.confirmPopup(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                payment_lines: [
                    { name: "Bank", amount: "10.0" },
                    { name: "Customer Account", amount: "-10.0" },
                ],
            }),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_simplified_invoice_not_override_set_pricelist", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickPriceList("Test pricelist"),
            ProductScreen.clickFiscalPosition("Original Tax"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});
