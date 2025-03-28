import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import { registry } from "@web/core/registry";

//This tour is meant to be run on all localizations
registry.category("web_tour.tours").add("generic_localization_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            ProductScreen.clickDisplayedProduct("Small Shelf"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ProductScreen.closePos(),
            Dialog.confirm("Close Register"),
            Chrome.endTour(),
        ].flat(),
});
