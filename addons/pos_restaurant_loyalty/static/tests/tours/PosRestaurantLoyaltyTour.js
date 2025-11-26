import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosRestaurantRewardStay", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Water"),
            PosLoyalty.hasRewardLine("10% on your order", "-0.22", "1"),
            Chrome.clickPlanButton(),
            Chrome.clickBtn("second floor"),
            Chrome.clickBtn("main floor"),
            FloorScreen.clickTable("5"),
            PosLoyalty.hasRewardLine("10% on your order", "-0.22", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_loyalty_multi_device_deviceA", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Coca-Cola", "3"),
            PosLoyalty.hasRewardLine("Free Product - Coca-Cola", "-2.20", "1"),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_loyalty_multi_device_deviceB", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("5"),
            PosLoyalty.hasRewardLine("Free Product - Coca-Cola", "-2.20", "1"),
            ProductScreen.orderLineHas("Coca-Cola", "3.0"),
        ].flat(),
});
