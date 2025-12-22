import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as PartnerList from "@point_of_sale/../tests/tours/utils/partner_list_util";
import * as Utils from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";
import { checkSimplifiedInvoiceNumber, checkCompanyState, pay } from "./utils/receipt_util";

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
            checkCompanyState("Badajoz"),
            ReceiptScreen.clickNextOrder(),

            ProductScreen.addOrderline("Desk Pad", "1"),
            pay(),
            checkSimplifiedInvoiceNumber("0003"),
            checkCompanyState("Badajoz"),
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
                trigger: "div.o_popover :contains('Settle Due Accounts')",
                content: "Check the popover opened",
                run: "click",
            },
            Utils.selectButton("Bank"),
            PaymentScreen.clickValidate(),
            Chrome.confirmPopup(),
            ReceiptScreen.isShown(),
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
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_simplified_partner_inactive_case", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});
