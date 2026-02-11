import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import { GenericHooks } from "@point_of_sale/../tests/pos/tours/utils/generic_hooks";
import { registry } from "@web/core/registry";

//This tour is meant to be run on all localizations
registry.category("web_tour.tours").add("generic_localization_tour", {
    undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps ) #245680
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
            FeedbackScreen.isShown(),
            GenericHooks.afterValidateHook(),
            {
                timeout: 20000,
                content: "feedback screen has finished the validation",
                trigger: ".feedback-screen .button.validation:not([disabled])",
            },
            FeedbackScreen.clickNextOrder(),
            ProductScreen.isShown(),
            Chrome.endTour(),
        ].flat(),
});
