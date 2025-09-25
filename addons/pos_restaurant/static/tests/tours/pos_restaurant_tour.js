import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { registry } from "@web/core/registry";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as TextInputPopup from "@point_of_sale/../tests/generic_helpers/text_input_popup_util";
import * as PreparationReceipt from "@point_of_sale/../tests/pos/tours/utils/preparation_receipt_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import { checkPreparationTicketData } from "@point_of_sale/../tests/pos/tours/utils/preparation_receipt_util";
import {
    negate,
    negateStep,
    assertCurrentOrderDirty,
} from "@point_of_sale/../tests/generic_helpers/utils";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

registry.category("web_tour.tours").add("pos_restaurant_sync", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create a floating order. The idea is to have one of the draft orders be a floating order during the tour.
            FloorScreen.clickNewOrder(),

            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.setTab("Test"),
            Chrome.clickPlanButton(),

            // Create first order
            FloorScreen.clickTable("5"),
            Chrome.isTabActive("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            inLeftSide(Order.hasLine({ productName: "Coca-Cola", run: "dblclick" })),
            ProductScreen.clickDisplayedProduct("Water", true),
            ProductScreen.orderlineIsToOrder("Water"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            checkPreparationTicketData([
                { name: "Coca-Cola", qty: 1 },
                { name: "Water", qty: 1 },
            ]),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            checkPreparationTicketData([]),
            ProductScreen.totalAmountIs("4.40"),

            // Create 2nd order (paid)
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            ProductScreen.clickDisplayedProduct("Minute Maid", true),
            ProductScreen.totalAmountIs("4.40"),
            checkPreparationTicketData([
                { name: "Coca-Cola", qty: 1 },
                { name: "Minute Maid", qty: 1 },
            ]),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // order on another table with a product variant
            FloorScreen.orderCountSyncedInTableIs("5", "0"),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", false),
            {
                ...Dialog.confirm(),
                content: "validate the variant dialog (with default values)",
            },
            ProductScreen.selectedOrderlineHas("Desk Organizer"),
            checkPreparationTicketData([
                { name: "Desk Organizer", qty: 1, attributes: ["S", "Leather"] },
            ]),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("4"),
            ProductScreen.orderlinesHaveNoChange(),
            checkPreparationTicketData([]),
            ProductScreen.totalAmountIs("5.87"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // After clicking next order, floor screen is shown.
            // It should have 1 as number of draft synced order.
            FloorScreen.orderCountSyncedInTableIs("5", "0"),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("4.40"),

            // Create another draft order and go back to floor
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            ProductScreen.clickDisplayedProduct("Minute Maid", true),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("5", "0"),

            // Delete the first order then go back to floor
            Chrome.clickOrders(),
            // The order ref ends with -00002 because it is actually the 2nd order made in the session.
            // The first order made in the session is a floating order.
            TicketScreen.deleteOrder("002"),
            Dialog.confirm(),
            Chrome.closePrintingWarning(),
            Chrome.isSyncStatusConnected(),
            TicketScreen.selectOrder("005"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            Chrome.clickPlanButton(),

            // There should be 0 synced draft order as we already deleted -00002.
            FloorScreen.clickTable("5"),
            ProductScreen.orderIsEmpty(),
        ].flat(),
});

/* pos_restaurant_sync_second_login
 *
 * This tour should be run after the first tour is done.
 */
registry.category("web_tour.tours").add("pos_restaurant_sync_second_login", {
    steps: () =>
        [
            // There is one draft synced order from the previous tour
            Chrome.startPoS(),
            FloorScreen.clickTable("2"),
            Chrome.waitRequest(),
            ProductScreen.isShown(),
            {
                trigger: ".pos-leftheader .badge:contains(2)",
            },
            ProductScreen.totalAmountIs("4.40"),

            // Test transfering an order
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.orderCountSyncedInTableIs(2, 2),
            FloorScreen.clickTable("4"),
            Chrome.waitRequest(),
            ProductScreen.isShown(),
            {
                trigger: ".pos-leftheader .badge:contains(4)",
            },
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 1,
                withClass: ":eq(0)",
                price: 2.2,
            }),
            Order.hasLine({
                productName: "Minute Maid",
                quantity: 1,
                withClass: ":eq(1)",
                price: 2.2,
            }),

            // Test if products still get merged after transfering the order
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.clickNumpad("1"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            // At this point, there are no draft orders.

            FloorScreen.clickTable("2"),
            ProductScreen.isShown(),
            {
                trigger: ".pos-leftheader .badge:contains(2)",
            },
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.orderCountSyncedInTableIs(2, 0),
            FloorScreen.orderCountSyncedInTableIs(4, 0),
            FloorScreen.clickTable("4"),
            Chrome.waitRequest(),
            ProductScreen.isShown(),
            {
                trigger: ".pos-leftheader .badge:contains(4)",
            },
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.orderCountSyncedInTableIs("4", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("SaveLastPreparationChangesTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "1"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("5"),
            Chrome.waitRequest(),
            ProductScreen.orderlinesHaveNoChange(),
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 1,
                withClass: ":eq(0)",
            }),
            Chrome.clickPlanButton(),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_pos_restaurant_course", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickCourseButton(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickCourseButton(),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.clickCourseButton(),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("5"),
            // Check only 2 courses are there and empty course gets removed on clicking Order button
            {
                trigger: negate('.order-course-name:eq(2) > span:contains("Course 3")'),
            },
            ProductScreen.fireCourseButtonHighlighted("Course 2"),
            ProductScreen.payButtonNotHighlighted(),
            ProductScreen.clickCourseButton(),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.clickTable("5"),
            // Check only 2 courses are there and empty course gets removed on clicking Plan button
            {
                trigger: negate('.order-course-name:eq(2) > span:contains("Course 3")'),
            },
            // Check empty course gets remove after fire course.
            ProductScreen.clickCourseButton(),
            ProductScreen.selectCourseLine("Course 2"),
            ProductScreen.fireCourseButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("5"),
            {
                trigger: negate('.order-course-name:eq(2) > span:contains("Course 3")'),
            },
        ].flat(),
});

registry.category("web_tour.tours").add("OrderTrackingTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "2"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            inLeftSide([
                ...ProductScreen.clickLine("Coca-Cola", "2"),
                ...ProductScreen.selectedOrderlineHasDirect("Coca-Cola", "2"),
                ...["⌫", "1"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Coca-Cola", "1"),
            ]),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});
registry.category("web_tour.tours").add("CategLabelCheck", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Test Multi Category Product"),
            ProductScreen.OrderButtonNotContain("Drinks"),
        ].flat(),
});
registry.category("web_tour.tours").add("OrderChange", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "1"),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickNumpad("+10"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            TicketScreen.receiptChangeIs("10"),
        ].flat(),
});

registry.category("web_tour.tours").add("CrmTeamTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSPaymentSyncTour1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.emptyPaymentlines("2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSPaymentSyncTour2", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("5"),
            PaymentScreen.isShown(),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentlineDelButton("Bank", "2.20"),
            PaymentScreen.emptyPaymentlines("4.40"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSPaymentSyncTour3", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("5"),
            PaymentScreen.isShown(),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.remainingIs("2.2"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PreparationPrinterContent", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickControlButton("Guests"),
            NumberPopup.enterValue("5"),
            NumberPopup.isShown("5"),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Product Test"),
            Chrome.freezeDateTime(1739370000000),
            Dialog.confirm("Add"),
            // Cutomer Note on orderline
            ProductScreen.addCustomerNote("Test customer note - orderline"),
            ProductScreen.totalAmountIs("10"),
            checkPreparationTicketData([{ name: "Product Test", qty: 1, attribute: ["Value 1"] }], {
                visibleInDom: [
                    "14:20",
                    "Value 1",
                    "Guest: 5",
                    "Eat in",
                    "Test customer note - orderline",
                ],
                invisibleInDom: ["DUPLICATA!"],
            }),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickLine("Product Test"),
            ProductScreen.addCustomerNote("Updated customer note - orderline"),
            checkPreparationTicketData([{ name: "Product Test", qty: 1, attribute: ["Value 1"] }], {
                visibleInDom: ["NOTE UPDATE", "Updated customer note - orderline"],
            }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Water"),
            ...ProductScreen.clickSelectedLine("Water"),
            ProductScreen.addInternalNote("To Serve"),
            checkPreparationTicketData([{ name: "Water", qty: 1 }], {
                visibleInDom: ["14:20", "To Serve"],
                invisibleInDom: ["colorIndex"],
            }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.selectPreset("Eat in", "Takeaway"),
            Chrome.selectPresetTimingSlotHour("12:00"),
            Chrome.presetTimingSlotIs("12:00"),
            checkPreparationTicketData([{ name: "Water", qty: 1 }], {
                visibleInDom: ["12:00", "Takeaway"],
                invisibleInDom: ["colorIndex"],
            }),
        ].flat(),
});

registry.category("web_tour.tours").add("test_course_restaurant_preparation_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickCourseButton(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickCourseButton(),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.clickCourseButton(),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            checkPreparationTicketData(
                [
                    { name: "Coca-Cola", qty: 1 },
                    { name: "Water", qty: 1 },
                    { name: "Minute Maid", qty: 1 },
                ],
                {
                    visibleInDom: ["Course 1", "Course 2", "Course 3"],
                }
            ),
            ProductScreen.clickOrderButton(),
            Dialog.bodyIs("Preparation Printer: The printer is not reachable."),
            Dialog.confirm(),
            FloorScreen.clickTable("5"),
            checkPreparationTicketData([], {
                visibleInDom: ["Course 2"],
                fireCourse: true,
            }),
            ProductScreen.fireCourseButton(),
            Dialog.bodyIs("Printer: The printer is not reachable."),
            Dialog.confirm(),
            FloorScreen.clickTable("5"),
            ProductScreen.selectCourseLine("Course 3"),
            checkPreparationTicketData([{ name: "Product Test", qty: 1, attribute: ["Value 1"] }], {
                visibleInDom: ["Course 3"],
                invisibleInDom: ["DUPLICATA!"],
                fireCourse: true,
            }),
            ProductScreen.fireCourseButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_preparation_receipt", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 1"),
            combo.select("Combo Product 5"),
            combo.select("Combo Product 8"),
            Dialog.confirm(),
            checkPreparationTicketData([
                { name: "Office Combo", qty: 1 },
                { name: "Combo Product 2", qty: 1 },
                { name: "Combo Product 4", qty: 1 },
                { name: "Combo Product 6", qty: 1 },
                { name: "Office Combo", qty: 1 },
                { name: "Combo Product 1", qty: 1 },
                { name: "Combo Product 5", qty: 1 },
                { name: "Combo Product 8", qty: 1 },
            ]),
            ProductScreen.totalAmountIs("95.00"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
        ].flat(),
});

registry.category("web_tour.tours").add("MultiPreparationPrinter", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product 1"),
            ProductScreen.clickOrderButton(),
            Dialog.bodyIs("Printer 2: The printer is not reachable."),
            Dialog.confirm(),
        ].flat(),
});

registry.category("web_tour.tours").add("LeaveResidualOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
        ].flat(),
});

registry.category("web_tour.tours").add("FinishResidualOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.orderCountSyncedInTableIs("5", "0"),
            FloorScreen.clickTable("5"),
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 1,
                withClass: ":eq(0)",
            }),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_multiple_preparation_printer_different_categories", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Product 1"),
            ProductScreen.clickDisplayedProduct("Product 2"),
            ProductScreen.clickOrderButton(),
            Dialog.bodyIs("Printer 1: The printer is not reachable."),
            Dialog.bodyIs("Printer 2: The printer is not reachable."),
            Dialog.confirm(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_preset_timing_restaurant", {
    steps: () =>
        [
            Chrome.freezeDateTime(1749965940000), // June 15, 2025
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickNewOrder(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectPreset("Eat in", "Takeaway"),
            TextInputPopup.inputText("John"),
            Dialog.confirm(),
            Chrome.selectPresetTimingSlotHour("12:00"),
            Chrome.presetTimingSlotIs("12:00"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(1, "John"),
            TicketScreen.nthRowContains(1, "Takeaway", false),
            TicketScreen.nthRowNotContains(1, "06/15/2025", false),
            TicketScreen.nthRowContains(2, "002"),
            TicketScreen.nthRowContains(2, "Eat in", false),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.selectPreset("Eat in", "Takeaway"),
            Chrome.selectPresetDateButton("06/16/2025"),
            Chrome.selectPresetTimingSlotHour("11:00"),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(3, "06/16/2025", false),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_preparation_receipt_layout", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            checkPreparationTicketData([
                { name: "Office Combo", qty: 1 },
                { name: "Combo Product 2", qty: 1 },
                { name: "Combo Product 4", qty: 1 },
                { name: "Combo Product 6", qty: 1 },
            ]),
        ].flat(),
});

registry.category("web_tour.tours").add("test_customer_alone_saved", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickOrders(),
            Chrome.clickRegister(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Deco Addict"),
            Chrome.clickOrders(),
            Chrome.clickRegister(),
            ProductScreen.customerIsSelected("Deco Addict"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_open_default_register_screen_config", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.endTour(),
        ].flat(),
});

registry
    .category("web_tour.tours")
    .add(
        "test_fast_payment_validation_from_restaurant_product_screen_with_automatic_receipt_printing",
        {
            steps: () =>
                [
                    Chrome.startPoS(),
                    Dialog.confirm("Open Register"),
                    FloorScreen.clickTable("2"),
                    ProductScreen.clickDisplayedProduct("Coca-Cola"),
                    {
                        content: "Check the content of the preparation receipt",
                        trigger: "body",
                        run: async () => {
                            const receipts = await PreparationReceipt.generatePreparationReceipts();
                            if (!receipts[0].innerHTML.includes("Coca-Cola")) {
                                throw new Error("Coca-Cola not found in printed receipt");
                            }
                            if (!receipts[0].innerHTML.includes("NEW")) {
                                throw new Error("NEW not found in printed receipt");
                            }
                        },
                    },
                    ProductScreen.clickFastPaymentButton("Bank"),
                    Dialog.discard(),
                    FeedbackScreen.isShown(),
                    Dialog.confirm(),
                    FeedbackScreen.clickScreen(),
                    FloorScreen.isShown(),
                    FloorScreen.clickTable("2"),
                    ProductScreen.clickDisplayedProduct("Coca-Cola"),
                    {
                        content: "Check the content of the preparation receipt",
                        trigger: "body",
                        run: async () => {
                            const receipts = await PreparationReceipt.generatePreparationReceipts();
                            if (!receipts[0].innerHTML.includes("Coca-Cola")) {
                                throw new Error("Coca-Cola not found in printed receipt");
                            }
                            if (!receipts[0].innerHTML.includes("NEW")) {
                                throw new Error("NEW not found in printed receipt");
                            }
                        },
                    },
                    ProductScreen.clickPayButton(false),
                    ProductScreen.discardOrderWarningDialog(),
                    PaymentScreen.clickPaymentMethod("Bank"),
                    PaymentScreen.clickValidate(),
                    FeedbackScreen.isShown(),
                    Dialog.confirm(),
                    FeedbackScreen.clickScreen(),
                    FloorScreen.isShown(),
                ].flat(),
        }
    );

registry
    .category("web_tour.tours")
    .add(
        "test_fast_payment_validation_from_restaurant_product_screen_without_automatic_receipt_printing",
        {
            steps: () =>
                [
                    Chrome.startPoS(),
                    Dialog.confirm("Open Register"),
                    FloorScreen.clickTable("2"),
                    ProductScreen.clickDisplayedProduct("Coca-Cola"),
                    {
                        content: "Check the content of the preparation receipt",
                        trigger: "body",
                        run: async () => {
                            const receipts = await PreparationReceipt.generatePreparationReceipts();
                            if (!receipts[0].innerHTML.includes("Coca-Cola")) {
                                throw new Error("Coca-Cola not found in printed receipt");
                            }
                            if (!receipts[0].innerHTML.includes("NEW")) {
                                throw new Error("NEW not found in printed receipt");
                            }
                        },
                    },
                    ProductScreen.clickFastPaymentButton("Bank"),
                    Dialog.discard(),
                    ReceiptScreen.isShown(),
                    ReceiptScreen.clickNextOrder(),
                    FloorScreen.isShown(),
                    FloorScreen.clickTable("2"),
                    ProductScreen.clickDisplayedProduct("Coca-Cola"),
                    {
                        content: "Check the content of the preparation receipt",
                        trigger: "body",
                        run: async () => {
                            const receipts = await PreparationReceipt.generatePreparationReceipts();
                            if (!receipts[0].innerHTML.includes("Coca-Cola")) {
                                throw new Error("Coca-Cola not found in printed receipt");
                            }
                            if (!receipts[0].innerHTML.includes("NEW")) {
                                throw new Error("NEW not found in printed receipt");
                            }
                        },
                    },
                    ProductScreen.clickPayButton(false),
                    ProductScreen.discardOrderWarningDialog(),
                    PaymentScreen.clickPaymentMethod("Bank"),
                    PaymentScreen.clickValidate(),
                    ReceiptScreen.isShown(),
                    ReceiptScreen.clickNextOrder(),
                    FloorScreen.isShown(),
                ].flat(),
        }
    );

registry.category("web_tour.tours").add("test_transfering_orders", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create a floating order with 3 cola
            FloorScreen.clickNewOrder(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.setTab("Cola"),
            Chrome.clickPlanButton(),

            // Create a floating order with 3 water
            FloorScreen.clickNewOrder(),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.setTab("Water"),
            Chrome.clickPlanButton(),

            // Create an order on table 5 with 3 minute maid
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            Chrome.clickPlanButton(),

            // Create an order on table 4 with 3 coca-cola
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),

            // Should have 4 orders
            Chrome.clickOrders(),
            TicketScreen.nbOrdersIs(4),

            // Transfer floating order to another floating order
            TicketScreen.selectOrder("Cola"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.clickControlButton("Transfer"),
            Chrome.clickOrders(),
            TicketScreen.selectOrder("Water"),
            ProductScreen.isShown(),
            ProductScreen.clickLine("Coca-Cola", "3"),
            ProductScreen.clickLine("Water", "3"),
            Chrome.clickOrders(),
            TicketScreen.nbOrdersIs(3),

            // Transfering order from table 5 to table 4
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("4"),
            ProductScreen.clickLine("Minute Maid", "3"),
            ProductScreen.clickLine("Coca-Cola", "3"),
            Chrome.clickOrders(),
            TicketScreen.nbOrdersIs(2),

            // Transfering order from table to floating order
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickControlButton("Transfer"),
            Chrome.clickOrders(),
            TicketScreen.selectOrder("Water"),
            ProductScreen.isShown(),
            ProductScreen.clickLine("Coca-Cola", "6"),
            ProductScreen.clickLine("Water", "3"),
            ProductScreen.clickLine("Minute Maid", "3"),
            Chrome.clickOrders(),
            TicketScreen.nbOrdersIs(1),

            // Transfering floating order to empty table
            TicketScreen.selectOrder("Water"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickLine("Coca-Cola", "6"),
            ProductScreen.clickLine("Water", "3"),
            ProductScreen.clickLine("Minute Maid", "3"),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("5", "1"),

            // Create a new floating order and transfer it to filled table
            FloorScreen.clickNewOrder(),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.setTab("Water2"),
            Chrome.clickPlanButton(),
            Chrome.clickOrders(),
            TicketScreen.selectOrder("Water2"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickLine("Water", "4"),
            ProductScreen.clickLine("Coca-Cola", "6"),
            ProductScreen.clickLine("Minute Maid", "3"),
            Chrome.clickOrders(),
            TicketScreen.nbOrdersIs(1),
        ].flat(),
});
registry.category("web_tour.tours").add("test_direct_sales", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickNewOrder(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.syncCurrentOrder(),
            PaymentScreen.clickValidate(),

            Chrome.clickPlanButton(),
            FloorScreen.clickNewOrder(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.setTab("Test"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.syncCurrentOrder(),
            PaymentScreen.clickValidate(),

            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.syncCurrentOrder(),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_lines_qty_update", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickLine("Coca-Cola"),
            Chrome.waitRequest(), // Wait for sync request (the order is created)
            assertCurrentOrderDirty(false),
            Numpad.click("3"),
            Order.hasLine({ productName: "Coca-Cola", quantity: 3 }),
            assertCurrentOrderDirty(true),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            Chrome.waitRequest(), // Wait for sync request
            FloorScreen.clickTable("5"),
            ProductScreen.isShown(),
            assertCurrentOrderDirty(false),
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_set_partner", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            Chrome.waitRequest(), // Wait for sync request
            assertCurrentOrderDirty(false),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Deco Addict"),
            assertCurrentOrderDirty(true),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            Chrome.waitRequest(), // Wait for sync request
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_set_note", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            Chrome.waitRequest(), // Wait for sync request
            assertCurrentOrderDirty(false),
            ProductScreen.isShown(),
            ProductScreen.addInternalNote("Hello world"),
            assertCurrentOrderDirty(true),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            Chrome.waitRequest(), // Wait for sync request
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_set_line_note", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            Chrome.waitRequest(), // Wait for sync request
            assertCurrentOrderDirty(false),
            ProductScreen.isShown(),
            ProductScreen.clickLine("Coca-Cola"),
            ProductScreen.addInternalNote("Demo note"),
            assertCurrentOrderDirty(true),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            Chrome.waitRequest(), // Wait for sync request
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_set_pricelist", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            Chrome.waitRequest(), // Wait for sync request
            assertCurrentOrderDirty(false),
            ProductScreen.isShown(),
            ProductScreen.clickLine("Coca-Cola"),
            ProductScreen.clickPriceList("Restaurant Pricelist"),
            assertCurrentOrderDirty(true),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            Chrome.waitRequest(), // Wait for sync request
        ].flat(),
});

registry.category("web_tour.tours").add("test_delete_line_release_table", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickLine("Coca-Cola"),
            ProductScreen.selectedOrderlineHasDirect("Coca-Cola"),
            ...["⌫", "⌫"].map(Numpad.click),
            ProductScreen.releaseTable(),
            FloorScreen.clickTable("5"),
            Chrome.waitRequest(),
            negateStep(...Order.hasLine({ productName: "Coca-Cola" })),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_synchronisation", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A"),
            Chrome.clickPlanButton(),
            FloorScreen.hasTable("5"),
            FloorScreen.clickTable("5"),
            {
                content: "Check if there still has combo lines",
                trigger: ".orderline-combo",
            },
            ProductScreen.addCourse(),
            ProductScreen.clickOrderline("Combo Product 2"),
            ProductScreen.transferCourseTo("Course 2"),
            {
                content: "Check if entire combo is transfered to course 2",
                trigger: ".pos", // dummy trigger
                run: function () {
                    const onlyCourse2 = window.posmodel
                        .getOrder()
                        .lines.every((x) => x.course_id.name === "Course 2");

                    if (!onlyCourse2) {
                        throw new Error("The entire combo must be transferred to Course 2.");
                    }
                },
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_guest_count_bank_payment", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            ProductScreen.clickPayButton(false),
            ProductScreen.confirmOrderWarningDialog(),
            NumberPopup.enterValue("5"),
            NumberPopup.isShown("5"),
            Dialog.confirm(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
        ].flat(),
});
