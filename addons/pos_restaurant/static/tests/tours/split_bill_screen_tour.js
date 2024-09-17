import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
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
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("SplitBillScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("102"),
            ProductScreen.addOrderline("Water", "5", "2", "10.0"),
            ProductScreen.addOrderline("Minute Maid", "3", "2", "6.0"),
            ProductScreen.addOrderline("Coca-Cola", "1", "2", "2.0"),
            ProductScreen.clickControlButton("Split"),

            // Check if the screen contains all the orderlines
            SplitBillScreen.orderlineHas("Water", "5", "0"),
            SplitBillScreen.orderlineHas("Minute Maid", "3", "0"),
            SplitBillScreen.orderlineHas("Coca-Cola", "1", "0"),

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
            SplitBillScreen.clickPay(),
            ProductScreen.clickOrderline("Water", "3.0"),
            ProductScreen.clickOrderline("Coca-Cola", "1.0"),

            // go back to the original order and see if the order is changed
            Chrome.clickOrders(),
            TicketScreen.selectOrder("001"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderline("Water", "2.0"),
            ProductScreen.clickOrderline("Minute Maid", "3.0"),

            // Split the order of table 2 again
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("102"),
            ProductScreen.clickControlButton("Split"),

            SplitBillScreen.clickOrderline("Water"),
            SplitBillScreen.orderlineHas("Water", "2", "1"),
            SplitBillScreen.subtotalIs("2.0"),
            SplitBillScreen.clickOrderline("Minute Maid"),
            SplitBillScreen.orderlineHas("Minute Maid", "3", "1"),
            SplitBillScreen.subtotalIs("4.0"),

            SplitBillScreen.clickPay(),

            // go back to the original order and see if the order is changed
            Chrome.clickOrders(),
            TicketScreen.selectOrder("001"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderline("Water", "1.0"),
            ProductScreen.clickOrderline("Minute Maid", "2.0"),
        ].flat(),
});

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
            ProductScreen.clickControlButton("Split"),

            SplitBillScreen.clickOrderline("Water"),
            SplitBillScreen.orderlineHas("Water", "1", "1"),
            SplitBillScreen.clickOrderline("Coca-Cola"),
            SplitBillScreen.orderlineHas("Coca-Cola", "1", "1"),
            SplitBillScreen.clickPay(),
            Chrome.clickOrders(),
            TicketScreen.selectOrder("002"),
            TicketScreen.loadSelectedOrder(),
            Order.hasLine({ productName: "Coca-Cola", quantity: "1.0" }),
            Order.hasLine({ productName: "Water", quantity: "1.0" }),
            ProductScreen.totalAmountIs("4.00"),
            Chrome.clickOrders(),
            TicketScreen.selectOrder("001"),
            TicketScreen.loadSelectedOrder(),
            Order.hasLine({ productName: "Minute Maid", quantity: "1.0" }),
            ProductScreen.totalAmountIs("2.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("SplitBillScreenTour3", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Water", "2", "2", "4.00"),
            ProductScreen.clickControlButton("Split"),

            // Check if the screen contains all the orderlines
            SplitBillScreen.orderlineHas("Water", "2", "0"),

            // split 1 water
            SplitBillScreen.clickOrderline("Water"),
            SplitBillScreen.orderlineHas("Water", "2", "1"),
            SplitBillScreen.subtotalIs("2.0"),

            // click pay to split, and pay
            SplitBillScreen.clickPay(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickContinueOrder(),

            // Check if there is still water in the order
            ProductScreen.isShown(),
            ProductScreen.orderLineHas("Water", "1.0"),
            ProductScreen.clickPayButton(true),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            // Check if there is no more order to continue
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("SplitBillScreenTour4ProductCombo", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 3"),
            combo.select("Combo Product 5"),
            combo.select("Combo Product 8"),
            Dialog.confirm(),

            ...ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 7"),
            Dialog.confirm(),

            ProductScreen.addOrderline("Water", "1"),
            ProductScreen.addOrderline("Minute Maid", "1"),

            // The water and the first combo will go in the new splitted order
            // we will then check if the rest of the items from this combo
            // are automatically sent to the new order.
            ProductScreen.clickControlButton("Split"),
            SplitBillScreen.clickOrderline("Water"),
            SplitBillScreen.clickOrderline("Combo Product 3"),
            // we check that all the lines in the combo are splitted together
            SplitBillScreen.orderlineHas("Water", "1", "1"),
            SplitBillScreen.orderlineHas("Office Combo", "1", "1"),
            SplitBillScreen.orderlineHas("Combo Product 3", "1", "1"),
            SplitBillScreen.orderlineHas("Combo Product 5", "1", "1"),
            SplitBillScreen.orderlineHas("Combo Product 8", "1", "1"),
            SplitBillScreen.orderlineHas("Office Combo", "1", "1"),
            SplitBillScreen.orderlineHas("Combo Product 2", "1", "0"),
            SplitBillScreen.orderlineHas("Combo Product 4", "1", "0"),
            SplitBillScreen.orderlineHas("Combo Product 7", "1", "0"),

            ...SplitBillScreen.subtotalIs("53.80"),
            ...SplitBillScreen.clickPay(),
            ProductScreen.clickPayButton(),
            ...PaymentScreen.clickPaymentMethod("Bank"),
            ...PaymentScreen.clickValidate(),
            ...ReceiptScreen.clickContinueOrder(),

            // Check if there is still water in the order
            ...ProductScreen.isShown(),
            // now we check that all the lines that remained in the order are correct
            ...ProductScreen.orderLineHas("Minute Maid", "1.0"),
            ...ProductScreen.clickOrderline("Office Combo"),
            ...ProductScreen.selectedOrderlineHas("Office Combo", "1.0", "43.33"),
            ...ProductScreen.orderLineHas("Combo Product 2", "1.0"),
            ...ProductScreen.orderLineHas("Combo Product 4", "1.0"),
            ...ProductScreen.orderLineHas("Combo Product 7", "1.0"),
            ...ProductScreen.totalAmountIs("45.53"),
        ].flat(),
});
