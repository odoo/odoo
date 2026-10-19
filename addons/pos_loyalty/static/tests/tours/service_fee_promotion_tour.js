import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ServiceFeeFixedPromotionScalingTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // The quantity and the price of a fixed fee are the cashier's: the
            // promotion recomputing the order must not round them off.
            ProductScreen.clickDisplayedProduct("Item"),
            Order.hasServiceFee("10.00"),
            Order.hasLine({ productName: "10% on your order", price: "-5.00" }),
            ProductScreen.totalAmountIs("55.00"), // 50 + 10 - 5.

            // 3 x $10 = $30.00 exactly, and the discount stays where it is.
            ProductScreen.clickLine("Service Fee", "1"),
            ProductScreen.clickNumpad("3"),
            Order.hasServiceFee("30.00"),
            Order.hasLine({ productName: "10% on your order", price: "-5.00" }),
            ProductScreen.totalAmountIs("75.00"), // 50 + 30 - 5.

            // Pricing it at $4 a unit gives 3 x $4 = $12.00 (the line is still
            // selected), and leaves the discount at $5.00 again.
            ProductScreen.clickNumpad("Price", "4"),
            Order.hasServiceFee("12.00"),
            Order.hasLine({ productName: "10% on your order", price: "-5.00" }),
            ProductScreen.totalAmountIs("57.00"), // 50 + 12 - 5.
        ].flat(),
});

registry.category("web_tour.tours").add("ServiceFeePromotionExcludesFeeTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // A promotion on order is taken from what was ordered: 10% of the $50
            // product, not of the $55 the service fee brings the order to.
            ProductScreen.clickDisplayedProduct("Item"),
            Order.hasServiceFee("5.00"), // 10% of 50.
            Order.hasLine({ productName: "10% on your order", price: "-5.00" }), // Not -5.50.
            ProductScreen.totalAmountIs("50.00"), // 50 + 5 - 5.
        ].flat(),
});

registry.category("web_tour.tours").add("ServiceFeeRewardDeactivationTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // A fee based on the total after discount includes the reward line in
            // its base: 10% of (50 - 5).
            ProductScreen.clickDisplayedProduct("Item"),
            Order.hasLine({ productName: "10% on your order", price: "-5.00" }),
            Order.hasServiceFee("4.50"),
            ProductScreen.totalAmountIs("49.50"), // 50 - 5 + 4.50.

            // Deleting that line emits no event, so the fee used to keep the amount
            // the reward had reduced. It is 10% of the whole $50 again.
            PosLoyalty.removeRewardLine("10% on your order"),
            Order.doesNotHaveLine({ productName: "10% on your order" }),
            Order.hasServiceFee("5.00"),
            ProductScreen.totalAmountIs("55.00"), // 50 + 5.
            Order.serviceFeeLineCountIs(1),
        ].flat(),
});

registry.category("web_tour.tours").add("ServiceFeeFullDiscountTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // A promotion covering the whole order used to take the fee with it: a
            // fee carved out of a base of zero is no fee at all.
            ProductScreen.clickDisplayedProduct("Item"),
            Order.hasLine({ productName: "100% on your order", price: "-50.00" }),
            Order.hasServiceFee("10.00"), // The flat $10 stands: no discount applies to it.
            ProductScreen.totalAmountIs("10.00"), // 50 - 50 + 10.

            // Same before discount: the discount is no part of that total.
            ProductScreen.selectPreset("Fixed 10", "Percent 10 before discount"),
            Order.hasServiceFee("5.00"),
            ProductScreen.totalAmountIs("5.00"), // 50 - 50 + 5.

            // After discount, 10% of a fully discounted order is nothing to charge.
            ProductScreen.selectPreset("Percent 10 before discount", "Percent 10 after discount"),
            Order.doesNotHaveLine({ productName: "Service Fee" }),
            ProductScreen.totalAmountIs("0.00"),
        ].flat(),
});
