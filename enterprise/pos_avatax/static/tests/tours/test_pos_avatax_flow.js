import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";

registry.category("web_tour.tours").add("test_pos_avatax_flow", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Lumber Inc"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.totalAmountIs("5.10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            Chrome.endTour(),
        ].flat(),
});
