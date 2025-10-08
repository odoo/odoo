import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as DeviceSynchronization from "@pos_restaurant/../tests/tours/utils/devices_synchronization";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";

const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
const Chrome = { ...ChromePos, ...ChromeRestaurant };

registry.category("web_tour.tours").add("test_devices_synchronization", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),

            // product_screen
            // Check if lines created from another devices
            // correctly appear in the current device
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            DeviceSynchronization.createNewLine("Water", 2),
            ProductScreen.orderlineIsToOrder("Water"),
            DeviceSynchronization.changeLineQuantity("Water", 44),
            ProductScreen.checkTotalAmount(99.0),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Deco Addict"),
            Chrome.clickPlanButton(),

            // prpoduct_screen
            // Check if changing partner form another device
            // correctly appear in the current device
            FloorScreen.clickTable("5"),
            DeviceSynchronization.changePartner("Lumber Inc"),
            ProductScreen.customerIs("Lumber Inc"),

            // prpoduct_screen
            // Check if paying from another device
            // is correctly synchronized
            DeviceSynchronization.markOrderAsPaid(),
            ProductScreen.orderIsEmpty(),

            // floor_screen
            // Check if floor plan is correctly updated
            // when creating a new order from another device
            DeviceSynchronization.createNewOrderOnTable("5", [
                ["Coca-Cola", 1],
                ["Water", 2],
            ]),
            DeviceSynchronization.createNewOrderOnTable("4", [
                ["Coca-Cola", 50],
                ["Water", 30],
            ]),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("5", 3),
            FloorScreen.orderCountSyncedInTableIs("4", 80),
            FloorScreen.clickTable("5"),
            ProductScreen.checkTotalAmount(6.6),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.checkTotalAmount(176.0),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // product_screen
            // Check if creating an order one same table from two devices
            // is correctly handlded
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            DeviceSynchronization.createNewOrderOnTable(
                "5",
                [
                    ["Coca-Cola", 2],
                    ["Water", 2],
                ],
                false
            ),
            ProductScreen.orderLineHas("Coca-Cola", "2"),
            ProductScreen.orderLineHas("Water", "2"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.clickLine("Coca-Cola", 2),
            ProductScreen.clickLine("Coca-Cola", 1),
            ProductScreen.clickLine("Water", 3),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderSynchronisationTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            DeviceSynchronization.createNewOrderOnTable("4", [
                ["Coca-Cola", 50],
                ["Water", 30],
            ]),
            FloorScreen.clickTable("4"),
            ProductScreen.orderLineHas("Coca-Cola", "50.0"),
            DeviceSynchronization.markOrderAsPaid(),
            ProductScreen.isShown(),
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.checkStatus("device_sync", "Paid"),
            TicketScreen.selectOrder("device_sync"),
            TicketScreen.confirmRefund(),
        ].flat(),
});
