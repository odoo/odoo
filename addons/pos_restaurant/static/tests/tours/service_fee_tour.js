import { registry } from "@web/core/registry";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

function serviceFeeIsLastLine() {
    return {
        content: "the service fee is the last orderline of the order",
        trigger: `.order-container .orderline:last:has(.product-name:contains("Service Fee"))`,
    };
}

function serviceFeeBasedOnMentionIs(mention) {
    return {
        content: mention
            ? `the service fee is qualified with '${mention}'`
            : "the service fee carries no 'based on' mention",
        trigger: `.orderline:has(.product-name:contains("Service Fee")) .price-per-unit${
            mention ? `:contains("${mention}")` : `:not(:contains("discount"))`
        }`,
    };
}

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
            // A fixed fee is a flat amount no discount applies to, so `based on` has
            // nothing to qualify and must not be displayed.
            serviceFeeBasedOnMentionIs(false),

            // Test percentage service fee
            ProductScreen.selectPreset("Fixed", "Percentage before discount"),

            Order.hasServiceFee("0.22"), // Service fee should be 10% of 2.20
            ProductScreen.totalAmountIs("2.42"),
            // A percentage is taken from an order total, so it says which one.
            serviceFeeBasedOnMentionIs("(before discount)"),

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

registry.category("web_tour.tours").add("ServiceFeeQuantityTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // A fixed fee is a per-unit amount: editing its quantity must scale
            // it exactly, even though it inherits the product's 15% tax.
            FloorScreen.clickTable("5"),
            Chrome.isTabActive("5"),
            ProductScreen.clickDisplayedProduct("Taxed Dish"),
            Order.hasServiceFee("2.00"), // Fixed $2 fee (tax included) at quantity 1.

            // Set the service fee quantity to 5 -> it must become exactly $10.00,
            // not 9.99 (the bug: 5 x a rounded per-unit price).
            ProductScreen.clickLine("Service Fee", "1"),
            ProductScreen.clickNumpad("5"),
            Order.hasServiceFee("10.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("ServiceFeeMixedTaxQuantityTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Two products in different tax groups split the fixed fee into two
            // tax-group lines. Editing the quantity on one must still scale the whole
            // fee: it used to reset to 1 once the fee split into several lines (e.g. a
            // mixed-tax cart, or a promotion whose reward carries a different tax).
            FloorScreen.clickTable("5"),
            Chrome.isTabActive("5"),
            ProductScreen.clickDisplayedProduct("Dish A"),
            ProductScreen.clickDisplayedProduct("Dish B"),
            Order.hasServiceFee("1.50"), // $2 x 30/40, tax group A.
            Order.hasServiceFee("0.50"), // $2 x 10/40, tax group B.
            ProductScreen.totalAmountIs("42.00"), // 30 + 10 + 2.

            // Scale the fee to quantity 4: the two fee lines must become 6.00 and 2.00
            // (total 8.00), not stay stuck at 1.50 / 0.50 (the bug).
            ProductScreen.clickLine("Service Fee", "1"),
            ProductScreen.clickNumpad("4"),
            Order.hasServiceFee("6.00"),
            Order.hasServiceFee("2.00"),
            ProductScreen.totalAmountIs("48.00"), // 30 + 10 + 8.
        ].flat(),
});

registry.category("web_tour.tours").add("ServiceFeeCourseTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            FloorScreen.clickTable("5"),
            Chrome.isTabActive("5"),

            // Order a product: a service fee is added at the bottom.
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasServiceFee("10"),
            serviceFeeIsLastLine(),

            // Splitting the order into courses must not leave the fee stranded
            // in the first course: it belongs at the bottom of the last one.
            ProductScreen.addCourse(),
            ProductScreen.clickDisplayedProduct("Bruschetta"),
            Order.hasServiceFee("10"),
            serviceFeeIsLastLine(),

            // Adding yet another course keeps the fee at the very bottom.
            ProductScreen.addCourse(),
            ProductScreen.clickDisplayedProduct("Water"),
            Order.hasServiceFee("10"),
            serviceFeeIsLastLine(),
        ].flat(),
});

registry.category("web_tour.tours").add("ServiceFeeRefundTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Order two products with a 10% service fee, then pay.
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Bruschetta"),
            Order.hasServiceFee("1.07"), // 10% of 10.70.
            ProductScreen.totalAmountIs("11.77"),
            ProductScreen.clickPayButton(false),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),

            FloorScreen.clickTable("4"),
            ProductScreen.orderIsEmpty(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("001"),

            // Refund one of the two products.
            inLeftSide(Order.hasLine({ productName: "Coca-Cola", withClass: ".selected" })),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("1", "Coca-Cola"),

            // The service fee is an orderline like any other: the cashier decides
            // whether to give it back, so it must be selectable for refund.
            {
                content: "select the service fee line for refund",
                trigger: '.ticket-screen .orderline:has(.product-name:contains("Service Fee"))',
                run: "click",
            },
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("1", "Service Fee"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickBack(),
            ProductScreen.isShown(),

            // A refund order has no preset, so recompute must not touch it: the fee
            // stays exactly what was refunded (the whole 1.07), neither recomputed
            // down to 10% of the refunded product nor dropped for want of a preset.
            Order.hasServiceFee("1.07"),
            ProductScreen.totalAmountIs("-3.27"), // -(2.20 + 1.07).
            ...Chrome.waitForOrdersSync(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});
