import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_payment_method_close_session", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product 1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Urban Piper"),
            PaymentScreen.clickValidate(),
            Chrome.clickMenuOption("Close Register"),
            Dialog.confirm("Close Register"),
        ].flat(),
});
