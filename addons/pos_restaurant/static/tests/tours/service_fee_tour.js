import { registry } from "@web/core/registry";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

registry.category("web_tour.tours").add("ServiceFeeTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Test fixed amount service charge
            FloorScreen.clickTable("5"),
            Chrome.isTabActive("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            Order.hasServiceFee("10"), // Service fee should not change when adding a product with fixed amount.
            ProductScreen.totalAmountIs("12.20"),

            // Test percentage service fee
            ProductScreen.selectPreset("Fixed", "Percentage before discount"),

            Order.hasServiceFee("0.22"), // Service fee should be 10% of 2.20
            ProductScreen.totalAmountIs("2.42"),

            ProductScreen.clickDisplayedProduct("Bruschetta"),
            Order.hasServiceFee("1.07"), // Service fee should be 10% of 10.70 (2.20 + 8.50)
            ProductScreen.totalAmountIs("11.77"),

            // Test percentage service fee based on order total before discount
            inLeftSide([...ProductScreen.addDiscount("10")]),
            Order.hasServiceFee("1.07"), // Service fee should still be 10% of 10.70 because it's based on order total before discount
            ProductScreen.totalAmountIs("11.77"),

            // Test percentage service fee based on order total after discount
            ProductScreen.selectPreset("Percentage before discount", "Percentage after discount"),
            Order.hasServiceFee("0.99"), // Service fee is (2.20 + 8.50 * 0.9) * 10% = 0.99
            ProductScreen.totalAmountIs("10.84"),
        ].flat(),
});
