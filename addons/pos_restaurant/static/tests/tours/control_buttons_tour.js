import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as SplitBillScreen from "@pos_restaurant/../tests/tours/utils/split_bill_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

function activeTableIs(tableNumber) {
    return {
        trigger: `.table-free-order-label:contains("${tableNumber}")`,
    };
}

registry.category("web_tour.tours").add("ControlButtonsTour", {
    test: true,
    steps: () =>
        [
            // Test merging table, transfer is already tested in pos_restaurant_sync_second_login.
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("2"),
            activeTableIs("2"),
            ProductScreen.addOrderline("Water", "5", "2", "10.0"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            activeTableIs("4"),
            ProductScreen.addOrderline("Minute Maid", "3", "2", "6.0"),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("2"),
            activeTableIs("2"),
            Order.hasLine({ productName: "Water", quantity: "5" }),
            Order.hasLine({ productName: "Minute Maid", quantity: "3" }),

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
