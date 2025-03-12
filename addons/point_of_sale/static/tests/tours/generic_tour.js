import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import { GenericHooks } from "@point_of_sale/../tests/tours/utils/generic_hooks";
import { registry } from "@web/core/registry";

//This tour is meant to be run on all localizations
registry.category("web_tour.tours").add("generic_localization_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            GenericHooks.onProductScreen(),
            ProductScreen.clickDisplayedProduct("Test Product 1"),
            ProductScreen.clickDisplayedProduct("Test Product 2"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            GenericHooks.afterValidateHook(),
            ProductScreen.closePos(),
            Dialog.confirm("Close Register"),
            {
                trigger: "button:contains(backend)",
                run: "click",
                expectUnloadPage: true,
            },
            Chrome.endTour(),
        ].flat(),
});
