import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("pos_global_discount_tax_group", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.clickControlButton("Discount"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs(90),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_global_discount_tax_group_2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.clickControlButton("Discount"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs(108),
        ].flat(),
});

registry.category("web_tour.tours").add("test_invoice_order_with_global_discount", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductScreen.clickControlButton("Discount"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs("90.00"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAA"),
            ProductScreen.clickPayButton(),
            PaymentScreen.totalIs("90.00"),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.remainingIs("0.00"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptAmountTotalIs("90.00"),
        ].flat(),
});
