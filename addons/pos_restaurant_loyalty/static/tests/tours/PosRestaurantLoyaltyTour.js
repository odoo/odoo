import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosRestaurantRewardStay", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.totalAmountIs("1.98"),
            ProductScreen.back(),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("1.98"),
        ].flat(),
});
