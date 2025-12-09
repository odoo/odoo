import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("OnlinePaymentErrorsTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Letter Tray", "10"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.totalIs("48.0"),
            PaymentScreen.emptyPaymentlines("48.0"),

            PaymentScreen.clickPaymentMethod("Online payment"),
            PaymentScreen.selectedPaymentlineHas("Online payment", "48.0"),
            PaymentScreen.enterPaymentLineAmount("Online payment", "47"),
            PaymentScreen.selectedPaymentlineHas("Online payment", "47.0"),
            PaymentScreen.remainingIs("1.0"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "2"),
            PaymentScreen.selectedPaymentlineHas("Cash", "2.0"),
            PaymentScreen.changeIs("1.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            // successfully confirming the dialog would imply that the error popup is actually shown
            // Online payment line is now automatically deleted after the error popup
            Dialog.confirm(),
            PaymentScreen.remainingIs("46.0"),
            PaymentScreen.clickPaymentMethod("Online payment", true, { amount: "46.0" }),
            PaymentScreen.clickPaymentMethod("Online payment", true, {
                amount: "0.0",
                remaining: "0.0",
            }),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            // successfully confirming the dialog would imply that the error popup is actually shown
            // Online payment line is now automatically deleted after the error popup
            Dialog.confirm(),
            PaymentScreen.remainingIs("46.0"),
            PaymentScreen.clickPaymentMethod("Online payment", true, { amount: "46.0" }),
            PaymentScreen.clickPaymentMethod("Online payment"),
            PaymentScreen.clickPaymentline("Online payment", "0.0"),
            PaymentScreen.clickPaymentlineDelButton("Online payment", "0.0"),
            PaymentScreen.clickPaymentline("Cash", "2.0"),
            PaymentScreen.enterPaymentLineAmount("Cash", "3"),
            PaymentScreen.selectedPaymentlineHas("Cash", "3.0"),
            PaymentScreen.clickPaymentMethod("Online payment", true, { amount: "-1.0" }),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            // successfully confirming the dialog would imply that the error popup is actually shown
            // Online payment line is now automatically deleted after the error popup
            Dialog.confirm(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_selected_customer_after_adding_payment_sync", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Letter Tray", "10"),
            ProductScreen.selectedOrderlineHas("Letter Tray", "10.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.totalIs("48.0"),
            PaymentScreen.emptyPaymentlines("48.0"),
            PaymentScreen.clickPaymentMethod("Online payment"),
            PaymentScreen.selectedPaymentlineHas("Online payment", "48.0"),
            PaymentScreen.clickPartnerButton(),
            PaymentScreen.clickCustomer("A simple PoS man!"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            Dialog.is("Scan to Pay"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_mixed_payments_synced", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Letter Tray", "10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickNumpad("8"),
            PaymentScreen.selectedPaymentlineHas("Cash", "8.00"),
            PaymentScreen.clickPaymentMethod("Online payment"),
            PaymentScreen.clickPaymentlineDelButton("Online payment", "40.00"),
            PaymentScreen.clickPaymentline("Cash", "8.00"),
            PaymentScreen.clickNumpad("9"),
            PaymentScreen.selectedPaymentlineHas("Cash", "9.00"),
            PaymentScreen.clickPaymentMethod("Online payment"),
            PaymentScreen.selectedPaymentlineHas("Online payment", "39.00"),
            PaymentScreen.clickValidate(),
            {
                content: "Check Dialog title",
                trigger: '.modal .modal-header:contains("Scan to Pay")',
            }
        ].flat(),
});
