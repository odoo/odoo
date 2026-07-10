import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosDiscountServiceFeeTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("SF Product"),
            Order.hasServiceFee("2.00"), // fixed $2 fee, automatic

            // Apply a 20% global discount (pos_discount) -> -3.57 on the product.
            ProductScreen.clickControlButton("Discount"),
            Dialog.confirm(),
            Order.hasLine({ productName: "discount", price: "-3.57" }),

            // Scale the fee to quantity 2 -> $4.00 (exact), even under the discount.
            ProductScreen.clickLine("Service Fee", "1"),
            ProductScreen.clickNumpad("2"),
            Order.hasServiceFee("4.00"),
        ].flat(),
});
