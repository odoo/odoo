import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

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
