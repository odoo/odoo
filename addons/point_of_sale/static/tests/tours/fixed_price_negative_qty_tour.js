import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";

registry.category("web_tour.tours").add("FixedTaxNegativeQty", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Zero Amount Product", true, "1.0", "1.0"),
            ProductScreen.clickNumpad("+/-", "1"),
            ProductScreen.selectedOrderlineHas("Zero Amount Product", "-1.0", "-1.0"),

            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
            PaymentScreen.clickValidate(),

            ReceiptScreen.receiptIsThere(),
        ].flat(),
});
