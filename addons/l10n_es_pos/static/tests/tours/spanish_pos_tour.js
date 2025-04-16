import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
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
            },
            ReceiptScreen.clickNextOrder(),

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
});

registry.category("web_tour.tours").add("l10n_es_pos_settle_account_due", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("Partner Test 1"),
            {
                isActive: ["auto"],
                trigger: "div.o_popover :contains('Settle invoices')",
                content: "Check the popover opened",
                run: "click",
            },
            {
                trigger: "tr.o_data_row td[name='name']:contains('TSJ/2025/00001')",
                content: "Check the settle invoice line is present",
                run: "click",
            },
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Chrome.confirmPopup(),
            ReceiptScreen.isShown(),
            ReceiptScreen.paymentLineContains("Bank", "10.00"),
            ReceiptScreen.paymentLineContains("Customer Account", "-10.00"),
            Chrome.endTour(),
        ].flat(),
});
