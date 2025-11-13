import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import { GenericHooks } from "@point_of_sale/../tests/pos/tours/utils/generic_hooks";
import { registry } from "@web/core/registry";

//This tour is meant to be run on all localizations
registry.category("web_tour.tours").add("generic_localization_tour", {
    steps: () =>
        [
            Chrome.startPoS().map((step) => ({ ...step, timeout: 20000 })),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA Generic Partner"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            GenericHooks.afterValidateHook(),
            {
                timeout: 20000,
                content: "receipt screen is shown",
                trigger: ".pos .receipt-screen",
            },
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});
