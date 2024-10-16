import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosRestaurantRewardStay", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.totalAmountIs("1.98"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("1.98"),
        ].flat(),
});
