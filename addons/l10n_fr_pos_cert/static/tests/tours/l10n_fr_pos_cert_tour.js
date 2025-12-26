import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10nFrPosCertSelfInvoicingTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            {
                trigger: ".pos-receipt #posqrcode",
                content: "QR code is visible on the receipt",
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_old_unit_price_correctly_computed", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            Numpad.click("Price"),
            Numpad.click("5"),
            Numpad.click("6"),
            {
                content: "Check that old unit price",
                trigger: `.order-container .oldPrice s:contains("1.98")`,
            },
            ProductScreen.selectedOrderlineHas("Desk Pad", 1, "56.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            {
                content: "Check receipt old unit price",
                trigger: `.oldPrice s:contains("1.98")`,
            },
            ReceiptScreen.isShown(),
        ].flat(),
});
