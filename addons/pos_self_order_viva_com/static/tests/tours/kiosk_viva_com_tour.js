import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";

registry.category("web_tour.tours").add("kiosk_viva_com_payment", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        Utils.clickBtn("Pay"),
        // Confirmed by the status polling, which runs every 5 seconds.
        { ...ConfirmationPage.isShown(), timeout: 20000 },
    ],
});
