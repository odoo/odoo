import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as SplitBillScreen from "@pos_restaurant/../tests/tours/utils/split_bill_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as ChromePos from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ControlButtonsTour", {
    steps: () =>
        [
            // Test merging table, transfer is already tested in pos_restaurant_sync_second_login.
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("2"),
            Chrome.activeTableOrOrderIs("2"),
            ProductScreen.addOrderline("Water", "5", "2", "10.0"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            Chrome.activeTableOrOrderIs("4"),
            ProductScreen.addOrderline("Minute Maid", "3", "2", "6.0"),
            // Extra line is added to test merging table.
            // Merging this order to another should also include this extra line.
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectedOrderlineHas("Coca-Cola", "1"),

            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("2"),
            Chrome.activeTableOrOrderIs("2"),
            Order.hasLine({ productName: "Water", quantity: "5" }),
            Order.hasLine({ productName: "Minute Maid", quantity: "3" }),
            Order.hasLine({ productName: "Coca-Cola", quantity: "1" }),

            // Test SplitBillButton
            ProductScreen.clickControlButton("Split"),
            SplitBillScreen.clickBack(),

            ProductScreen.clickInternalNoteButton(),
            TextInputPopup.inputText("test note"),
            Dialog.confirm(),
            Order.hasLine({
                productName: "Water",
                quantity: "5",
                price: "10.0",
                internalNote: "test note",
                withClass: ".selected",
            }),
            // Check that note is imported if come back to the table
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            Order.hasLine({
                productName: "Water",
                quantity: "5",
                price: "10.0",
                internalNote: "test note",
                withClass: ".selected",
            }),

            ProductScreen.addOrderline("Water", "8", "1", "8.0"),

            // Test PrintBillButton
            ProductScreen.clickControlButton("Bill"),
            Dialog.is({ title: "Bill Printing" }),
            Dialog.cancel(),

            // Test GuestButton
            ProductScreen.clickControlButton("Guests"),
            NumberPopup.enterValue("15"),
            NumberPopup.isShown("15"),
            Dialog.confirm(),
            ProductScreen.guestNumberIs("15"),

            ProductScreen.clickControlButton("Guests"),
            NumberPopup.enterValue("5"),
            NumberPopup.isShown("5"),
            Dialog.confirm(),
            ProductScreen.guestNumberIs("5"),
        ].flat(),
});
