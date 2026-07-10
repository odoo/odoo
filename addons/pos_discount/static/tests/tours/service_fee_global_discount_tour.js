import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { registry } from "@web/core/registry";

// `:contains` is case insensitive and the preset names carry "discount" too:
// target the global discount button by its own class.
function clickGlobalDiscount() {
    return [
        ...ProductScreen.clickControlButtonMore(),
        {
            content: "click the global discount button",
            trigger: ".control-buttons button.js_discount",
            run: "click",
        },
    ];
}

registry.category("web_tour.tours").add("PosDiscountServiceFeePresetSwitchTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("SF Product"),
            Order.hasServiceFee("10.00"), // 10% of 100.
            ProductScreen.totalAmountIs("110.00"),

            // Creating the discount line emits no event the fee listens to, so
            // applying the discount recomputes the fee itself.
            clickGlobalDiscount(),
            Dialog.confirm(),
            Order.hasLine({ productName: "discount", price: "-20.00" }),
            Order.hasServiceFee("8.00"), // 10% of 100 - 20.
            ProductScreen.totalAmountIs("88.00"),
            Order.serviceFeeLineCountIs(1),

            // Reduced apart from the products, the discount line used to add a
            // second fee line on every recompute.
            ProductScreen.selectPreset(
                "Percent 10 after discount",
                "Percent 10 before discount",
                false
            ),
            Order.hasServiceFee("10.00"), // The discount is not part of the total the fee is taken from.
            ProductScreen.totalAmountIs("90.00"), // 100 - 20 + 10.
            Order.serviceFeeLineCountIs(1),

            ProductScreen.selectPreset(
                "Percent 10 before discount",
                "Percent 10 after discount",
                false
            ),
            Order.hasServiceFee("8.00"),
            ProductScreen.totalAmountIs("88.00"),
            Order.serviceFeeLineCountIs(1),

            // A discount covering the whole order leaves nothing to take a
            // percentage of, so the fee goes.
            clickGlobalDiscount(),
            NumberPopup.enterValue("100"),
            Dialog.confirm(),
            Order.hasLine({ productName: "discount", price: "-100.00" }),
            Order.doesNotHaveLine({ productName: "Service Fee" }),
            ProductScreen.totalAmountIs("0.00"),

            // ... but a fee taken from the total before discount is not concerned:
            // it is back to the full 10% of the products.
            ProductScreen.selectPreset(
                "Percent 10 after discount",
                "Percent 10 before discount",
                false
            ),
            Order.hasServiceFee("10.00"),
            ProductScreen.totalAmountIs("10.00"), // 100 - 100 + 10.
            Order.serviceFeeLineCountIs(1),
        ].flat(),
});
