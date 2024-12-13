import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as SplitBillScreen from "@pos_restaurant/../tests/tours/utils/split_bill_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ControlButtonsTour", {
    steps: () =>
        [
            // Test merging table, transfer is already tested in pos_restaurant_sync_second_login.
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("102"),
            ProductScreen.addOrderline("Water", "5", "2", "10.0"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("104"),
            ProductScreen.addOrderline("Minute Maid", "3", "2", "6.0"),
            // Extra line is added to test merging table.
            // Merging this order to another should also include this extra line.
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectedOrderlineHas("Coca-Cola", "1"),

            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("102"),
            Order.hasLine({ productName: "Water", quantity: "5" }),
            Order.hasLine({ productName: "Minute Maid", quantity: "3" }),
            Order.hasLine({ productName: "Coca-Cola", quantity: "1" }),

            // Test SplitBillButton
            ProductScreen.clickControlButton("Split"),
            SplitBillScreen.clickBack(),
            ProductScreen.clickLine("Water", "5"),
            ProductScreen.addInternalNote("test note", "Note"),
            Order.hasLine({
                productName: "Water",
                quantity: "5",
                price: "10.0",
                internalNote: "test note",
                withClass: ".selected",
            }),
            // Check that note is imported if come back to the table
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("102"),
            Order.hasLine({
                productName: "Water",
                quantity: "5",
                price: "10.0",
                internalNote: "test note",
            }),

            ProductScreen.addOrderline("Water", "8", "1", "8.0"),

            // Test PrintBillButton
            ProductScreen.clickControlButton("Bill"),
            Dialog.is({ title: "Bill Printing" }),
            Dialog.cancel(),

            // Test GuestButton
            ProductScreen.clickControlButton("Guests"),
            {
                content: `click numpad button: 1`,
                trigger: ".modal div.numpad button:contains(/^1$/)",
                run: "click",
            },
            {
                content: `click numpad button: 5`,
                trigger: ".modal div.numpad button:contains(/^5$/)",
                run: "click",
            },
            NumberPopup.isShown("15"),
            Dialog.confirm(),
            ProductScreen.guestNumberIs("15"),
            {
                content: `click guests 15 button`,
                trigger: `.modal .control-buttons button:contains(15Guests)`,
                run: "click",
            },
            {
                content: `click numpad button: 5`,
                trigger: ".modal div.numpad button:contains(/^5$/)",
                run: "click",
            },
            NumberPopup.isShown("5"),
            Dialog.confirm(),
            ProductScreen.guestNumberIs("5"),

            // Test Cancel Order Button
            Dialog.cancel(),
            Order.hasLine({ productName: "Water", quantity: "5" }),
            ProductScreen.clickControlButton("Cancel Order"),
            Dialog.confirm(),
            Order.doesNotHaveLine(),
            FloorScreen.isShown(),
        ].flat(),
});
