import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as SplitBillScreen from "@pos_restaurant/../tests/tours/utils/split_bill_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("SplitBillScreenTour2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Water", "1", "2.0"),
            ProductScreen.addOrderline("Minute Maid", "1", "2.0"),
            ProductScreen.addOrderline("Coca-Cola", "1", "2.0"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            Chrome.isSynced(),
            ProductScreen.clickControlButton("Split"),

            SplitBillScreen.clickOrderline("Water"),
            SplitBillScreen.orderlineHas("Water", "1", "1"),
            SplitBillScreen.clickOrderline("Coca-Cola"),
            SplitBillScreen.orderlineHas("Coca-Cola", "1", "1"),
            SplitBillScreen.clickButton("Split"),
            ProductScreen.totalAmountIs("4.0"),
            Chrome.clickOrders(),
            TicketScreen.selectOrder("2B"),
            TicketScreen.loadSelectedOrder(),
            Order.hasLine({ productName: "Coca-Cola", quantity: "1" }),
            Order.hasLine({ productName: "Water", quantity: "1" }),
            ProductScreen.totalAmountIs("4.00"),
            Chrome.clickOrders(),
            TicketScreen.selectOrder("001"),
            TicketScreen.loadSelectedOrder(),
            Order.hasLine({ productName: "Minute Maid", quantity: "1" }),
            ProductScreen.totalAmountIs("2.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("SplitBillScreenTourTransfer", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Water", "5", "2", "10.0"),
            ProductScreen.addOrderline("Minute Maid", "3", "2", "6.0"),
            ProductScreen.addOrderline("Coca-Cola", "1", "2", "2.0"),
            ProductScreen.clickControlButton("Discount"),
            Dialog.confirm(),
            ProductScreen.selectedOrderlineHas("discount", 1, "-1.80"),
            ProductScreen.clickControlButton("Split"),

            SplitBillScreen.globalDiscountIs("With 10% discount"),
            SplitBillScreen.clickBack(),
            ProductScreen.clickControlButton("Discount"),
            NumberPopup.clickType("fixed"),
            Dialog.confirm(),
            ProductScreen.clickControlButton("Split"),
            SplitBillScreen.globalDiscountIs("With $ 10.00 discount"),
            SplitBillScreen.clickBack(),
            ProductScreen.clickControlButton("Discount"),
            Dialog.confirm(),
            ProductScreen.clickControlButton("Split"),

            // Check if the screen contains all the orderlines
            SplitBillScreen.orderlineHas("Water", "5", "0"),
            SplitBillScreen.orderlineHas("Minute Maid", "3", "0"),
            SplitBillScreen.orderlineHas("Coca-Cola", "1", "0"),
            Order.doesNotHaveLine({ productName: "Discount" }),

            // split 3 water and 1 coca-cola
            SplitBillScreen.clickOrderline("Water"),
            SplitBillScreen.orderlineHas("Water", "5", "1"),
            SplitBillScreen.clickOrderline("Water"),
            SplitBillScreen.clickOrderline("Water"),
            SplitBillScreen.orderlineHas("Water", "5", "3"),
            SplitBillScreen.subtotalIs("6.0"),
            SplitBillScreen.clickOrderline("Coca-Cola"),
            SplitBillScreen.orderlineHas("Coca-Cola", "1", "1"),
            SplitBillScreen.subtotalIs("8.0"),

            // click pay to split, go back to check the lines
            SplitBillScreen.clickButton("Transfer"),
            FloorScreen.clickTable("5"),

            Order.doesNotHaveLine({ productName: "Discount" }),
            ProductScreen.totalAmountIs("8.0"),
            ProductScreen.clickOrderline("Water", "3"),
            ProductScreen.clickOrderline("Coca-Cola", "1"),

            // go back to the original order and see if the order is changed
            Chrome.clickOrders(),
            TicketScreen.selectOrder("001"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderline("Water", "2"),
            ProductScreen.clickOrderline("Minute Maid", "3"),
        ].flat(),
});
