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
import { delay } from "@odoo/hoot-dom";
import * as TextInputPopup from "@point_of_sale/../tests/generic_helpers/text_input_popup_util";
import * as PreparationReceipt from "@point_of_sale/../tests/pos/tours/utils/preparation_receipt_util";
import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

function checkOrderChanges(expected_changes) {
    return [
        {
            content: `Check order changes with expected changes ${JSON.stringify(
                expected_changes
            )}`,
            trigger: ".pos", // dummy trigger
            run: function () {
                const orderChanges = window.posmodel.getOrderChanges();
                const orderChangesKeys = Object.keys(orderChanges.orderlines);
                const orderChangesNbr = orderChangesKeys.length;
                // Quick check for lenght
                if (expected_changes.length !== orderChangesNbr) {
                    console.error(
                        `Was expecting ${expected_changes.length} order changes, got ${orderChangesNbr}`
                    );
                }
                for (const expected_change of expected_changes) {
                    const order_change_line = orderChangesKeys.find((key) => {
                        const change = orderChanges.orderlines[key];
                        return (
                            change.name === expected_change.name &&
                            change.quantity === expected_change.quantity
                        );
                    });
                    if (order_change_line === undefined) {
                        console.error(
                            `Was expecting product "${expected_change.name}" with quantity ${
                                expected_change.quantity
                            } as order change, inside ${JSON.stringify(orderChanges.orderlines)}`
                        );
                    }
                }
            },
        },
    ];
}

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
            checkOrderChanges([
                { name: "Water", quantity: 1 },
                { name: "Coca-Cola", quantity: 1 },
            ]),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            checkOrderChanges([]),
            ProductScreen.totalAmountIs("4.40"),

            // Create 2nd order (paid)
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            ProductScreen.clickDisplayedProduct("Minute Maid", true),
            ProductScreen.totalAmountIs("4.40"),
            checkOrderChanges([
                { name: "Coca-Cola", quantity: 1 },
                { name: "Minute Maid", quantity: 1 },
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.discardOrderWarningDialog(),
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
            checkOrderChanges([{ name: "Desk Organizer (S, Leather)", quantity: 1 }]),
            ProductScreen.clickOrderButton(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            FloorScreen.clickTable("4"),
            ProductScreen.orderlinesHaveNoChange(),
            checkOrderChanges([]),
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
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
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
            ProductScreen.totalAmountIs("4.40"),

            // Test transfering an order
            ProductScreen.clickControlButton("Transfer"),
            {
                trigger: ".table:contains(4)",
                async run(helpers) {
                    await delay(500);
                    await helpers.click();
                },
            },

            // Test if products still get merged after transfering the order
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.clickNumpad("1"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.discardOrderWarningDialog(),
            ReceiptScreen.clickNextOrder(),
            // At this point, there are no draft orders.

            {
                trigger: ".table:contains(2)",
                async run(helpers) {
                    await delay(500);
                    await helpers.click();
                },
            },
            ProductScreen.isShown(),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickControlButton("Transfer"),
            {
                trigger: ".table:contains(4)",
                async run(helpers) {
                    await delay(500);
                    await helpers.click();
                },
            },
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            Chrome.clickPlanButton(),
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
            FloorScreen.clickTable("5"),
            // Check only 2 courses are there and empty course gets removed on clicking Order button
            {
                trigger: negate('.order-course-name:eq(2) > span:contains("Course 3")'),
            },
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
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.discardOrderWarningDialog(),
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
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
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
            ProductScreen.clickPayButton(),
            PaymentScreen.emptyPaymentlines("2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
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
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentlineDelButton("Bank", "2.20"),
            PaymentScreen.emptyPaymentlines("4.40"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
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
            ProductScreen.clickPayButton(),
            PaymentScreen.remainingIs("2.2"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
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
            ProductScreen.clickDisplayedProduct("Product Test"),
            Chrome.freezeDateTime(1739370000000),
            Dialog.confirm("Add"),
            ProductScreen.totalAmountIs("10"),
            {
                content: "Check if order preparation contains always Variant",
                trigger: "body",
                run: async () => {
                    const receipts = await PreparationReceipt.generatePreparationReceipts();
                    if (!receipts[0].innerHTML.includes("Value 1")) {
                        throw new Error("Value 1 not found in printed receipt");
                    }
                    if (!receipts[0].innerHTML.includes("14:20")) {
                        throw new Error("14:20 not found in printed receipt");
                    }
                    if (!receipts[0].innerHTML.includes("Eat in")) {
                        throw new Error("Eat in not found in printed receipt");
                    }
                    if (receipts[0].innerHTML.includes("DUPLICATA!")) {
                        throw new Error("DUPLICATA! should not be present in printed receipt");
                    }
                },
            },
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Water"),
            ...ProductScreen.clickSelectedLine("Water"),
            ProductScreen.addInternalNote("To Serve"),
            {
                content: "Check if order preparation contains 'To Serve' order level internal note",
                trigger: "body",
                run: async () => {
                    const receipts = await PreparationReceipt.generatePreparationReceipts();
                    if (!receipts[0].innerHTML.includes("Water")) {
                        throw new Error("'Water' not found in printed receipt");
                    }
                    if (!receipts[1].innerHTML.includes("INTERNAL NOTE")) {
                        throw new Error("'INTERNAL NOTE' not found in printed receipt");
                    }
                    if (!receipts[1].innerHTML.includes("To Serve")) {
                        throw new Error("To Serve not found in printed receipt");
                    }
                    if (receipts[1].innerHTML.includes("colorIndex")) {
                        throw new Error("colorIndex should not be displayed in printed receipt");
                    }
                },
            },
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.selectPreset("Eat in", "Takeaway"),
            Chrome.selectPresetTimingSlotHour("12:00"),
            Chrome.presetTimingSlotIs("12:00"),
            {
                content: "Check if order preparation order contains Takeaway and its timing slot",
                trigger: "body",
                run: async () => {
                    const receipts = await PreparationReceipt.generatePreparationReceipts();
                    if (!receipts[0].innerHTML.includes("Takeaway")) {
                        throw new Error("Takeaway not found in printed receipt");
                    }
                    if (!receipts[0].innerHTML.includes("12:00")) {
                        throw new Error("12:00 not found in printed receipt");
                    }
                },
            },
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
            {
                content: "Check if order preparation contains courses with products",
                trigger: "body",
                run: async () => {
                    const receipts = await PreparationReceipt.generatePreparationReceipts();
                    const coursesAndProducts = [
                        { course: "Course 1", product: "Coca-Cola" },
                        { course: "Course 2", product: "Water" },
                        { course: "Course 3", product: "Minute Maid" },
                    ];
                    const courseEls = receipts[0].querySelectorAll("div.fw-bold");
                    const productEls = receipts[0].querySelectorAll(".product-name");

                    coursesAndProducts.forEach(({ course, product }) => {
                        const courseFound = Array.from(courseEls).some((el) =>
                            el.textContent.includes(course)
                        );
                        const productFound = Array.from(productEls).some((el) =>
                            el.textContent.includes(product)
                        );

                        if (!courseFound || !productFound) {
                            throw new Error(
                                `"${course}" or "${product}" not found in printed receipt`
                            );
                        }
                    });
                },
            },
            ProductScreen.clickOrderButton(),
            Dialog.bodyIs("Failed in printing Preparation Printer, Printer changes of the order"),
            Dialog.confirm(),
            FloorScreen.clickTable("5"),
            ProductScreen.selectCourseLine("Course 2"),
            {
                content: "Check if 'Course 2' is printed on the receipt",
                trigger: "body",
                run: async () => {
                    const receipts = await PreparationReceipt.generateFireCourseReceipts();
                    if (!receipts[0].innerHTML.includes("Course 2 fired")) {
                        throw new Error("'Course 2 fired' not found on printed receipt");
                    }
                },
            },
            ProductScreen.fireCourseButton(),
            Dialog.bodyIs("Failed in printing Preparation Printer, Printer changes of the order"),
            Dialog.confirm(),
            FloorScreen.clickTable("5"),
            ProductScreen.selectCourseLine("Course 3"),
            {
                content: "Check if 'Course 3' is printed on the receipt",
                trigger: "body",
                run: async () => {
                    const receipts = await PreparationReceipt.generateFireCourseReceipts();
                    if (!receipts[0].innerHTML.includes("Course 3 fired")) {
                        throw new Error("'Course 3 fired' not found on printed receipt");
                    }
                },
            },
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
            {
                content: "Check if order preparation has product correctly ordered",
                trigger: "body",
                run: async () => {
                    const receipts = await PreparationReceipt.generatePreparationReceipts();
                    const orderLines = [...receipts[0].querySelectorAll(".orderline")];
                    const orderLinesInnerText = orderLines.map((orderLine) => orderLine.innerText);
                    const expectedOrderLines = [
                        "Office Combo",
                        "Combo Product 2",
                        "Combo Product 4",
                        "Combo Product 6",
                        "Office Combo",
                        "Combo Product 1",
                        "Combo Product 5",
                        "Combo Product 8",
                    ];
                    for (let i = 0; i < orderLinesInnerText.length; i++) {
                        if (!orderLinesInnerText[i].includes(expectedOrderLines[i])) {
                            throw new Error("Order line mismatch");
                        }
                    }
                },
            },
            ProductScreen.totalAmountIs("95.00"),
            ProductScreen.clickPayButton(),
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
            Dialog.bodyIs("Failed in printing Printer 2 changes of the order"),
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
            ReceiptScreen.discardOrderWarningDialog(),
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
            FloorScreen.orderCountSyncedInTableIs("5", "1"),
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
            ReceiptScreen.discardOrderWarningDialog(),
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
            Dialog.bodyIs("Failed in printing Printer 1, Printer 2 changes of the order"),
            Dialog.confirm(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_preset_timing_restaurant", {
    steps: () =>
        [
            Chrome.startPoS(),
            Chrome.freezeDateTime(1749965940000), // June 15, 2025
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
            {
                trigger: "body",
                run: async () => {
                    const receipts = await PreparationReceipt.generatePreparationReceipts();

                    const comboItemLines = [...receipts[0].querySelectorAll(".orderline.ms-5")].map(
                        (el) => el.innerText
                    );
                    const expectedComboItemLines = [
                        "1 Combo Product 2",
                        "1 Combo Product 4",
                        "1 Combo Product 6",
                    ];
                    if (
                        comboItemLines.length !== expectedComboItemLines.length ||
                        !comboItemLines.every((line, index) =>
                            line.includes(expectedComboItemLines[index])
                        )
                    ) {
                        throw new Error("Order line mismatch");
                    }
                },
            },
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
