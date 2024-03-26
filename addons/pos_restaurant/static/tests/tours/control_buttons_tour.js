/** @odoo-module */

import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as SplitBillScreen from "@pos_restaurant/../tests/tours/utils/split_bill_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ControlButtonsTour", {
    test: true,
    steps: () =>
        [
            // Test TransferOrderButton
            Dialog.confirm("Open session"),
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Water", "5", "2", "10.0"),
            ProductScreen.clickControlButtonMore(),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),
            FloorScreen.backToFloor(),
            FloorScreen.clickTable("2"),
            ProductScreen.orderIsEmpty(),
            FloorScreen.backToFloor(),
            FloorScreen.clickTable("4"),

            // Test SplitBillButton
            ProductScreen.clickControlButtonMore(),
            ProductScreen.clickControlButton("Split"),
            SplitBillScreen.clickBack(),

            ProductScreen.clickControlButtonMore(),
            ProductScreen.clickControlButton("Internal Note"),
            TextInputPopup.inputText("test note"),
            Dialog.confirm(),
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
            ProductScreen.clickControlButtonMore(),
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
