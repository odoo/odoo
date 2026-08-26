import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as UniqueCode from "@pos_unique_code/../tests/helpers/unique_code_popup_util";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_kiosk_unique_code", {
    steps: () =>
        [
            Utils.clickBtn("Order Now"),
            ProductPage.clickProduct("Coca-Cola"),
            Utils.clickBtn("Checkout"),
            Utils.clickBtn("Order"),

            // A used code is refused and the popup stays open.
            UniqueCode.enterCode("22222"),
            UniqueCode.confirm(),
            UniqueCode.isRejected("This code has already been used"),
            UniqueCode.enterCode("11111"),
            UniqueCode.confirm(),
            Utils.clickBtn("Close"),
        ].flat(),
});
