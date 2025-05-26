import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import { registry } from "@web/core/registry";

const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
const Chrome = { ...ChromePos, ...ChromeRestaurant };

registry.category("web_tour.tours").add("test_table_merge_slow_network", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            FloorScreen.clickFloor("Main Floor"),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),

            FloorScreen.isShown(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Water"),
            Chrome.clickPlanButton(),

            FloorScreen.isShown(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Minute Maid", 2),
            Chrome.clickPlanButton(),

            FloorScreen.isShown(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),
            ProductScreen.isShown(),
        ].flat(),
});
