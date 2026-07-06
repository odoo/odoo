import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor, press, queryAll, tick, queryOne, edit } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as ResUiUtils from "@pos_restaurant/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...ResUiUtils };

definePosModels();

async function setupFloorTest() {
    const store = await setupPosEnv();
    store.session.state = "opened";
    store.config.set_tip_after_payment = false;
    return store;
}

async function mountFloorScreen(store) {
    store.router.state.current = "FloorScreen";
    store.router.state.params = {};
    const screen = await mountWithCleanup(FloorScreen);
    await animationFrame();
    return screen;
}

function getVisibleTableNumbers() {
    return queryAll(".o_fp_table .o_fp_table_number").map((el) => el.textContent.trim());
}

test("OrderChangeTour: add product, send order, pay with cash change", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickOrderButton();
    await animationFrame();
    await Utils.clickPlanButton();
    await Utils.clickTable("1");

    const order = store.getOrder();
    expect(order.preparationChanges.quantity).toBe(0);

    await Utils.clickPayButton();
    await Utils.clickPaymentMethod("Cash");
    await animationFrame();
    if (Utils.isMobile()) {
        await Utils.sendBufferKeys("+10");
    } else {
        await contains('.numpad button:contains("+10")').click();
        await animationFrame();
    }
    await Utils.clickValidatePayment();

    expect(order.state).toBe("paid");
});

test("SplitBillScreenTour: split items, verify both orders, split again", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickControlButton("Split");
    await waitFor(".splitbill-screen");

    expect(Utils.queryEl(".splitbill-screen .orderline .product-name", "TEST")).not.toBe(null);
    expect(Utils.queryEl(".splitbill-screen .orderline .product-name", "TEST 2")).not.toBe(null);

    await Utils.clickSplitOrderline("TEST");
    await Utils.clickSplitOrderline("TEST");
    await Utils.clickSplitOrderline("TEST");
    await Utils.clickSplitAction("Split");
    await animationFrame();

    const splitOrder = store.getOrder();
    expect(splitOrder.lines.length).toBe(1);
    const testLine = splitOrder.lines.find((l) => l.product_id.display_name === "TEST");
    const test2Line = splitOrder.lines.find((l) => l.product_id.display_name === "TEST 2");
    expect(testLine.qty).toBe(3);
    expect(test2Line).toBe(undefined);

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketOrder("001");
    await Utils.loadSelectedOrder();

    const originalOrder = store.getOrder();
    const origTest = originalOrder.lines.find((l) => l.product_id.display_name === "TEST");
    const origTest2 = originalOrder.lines.find((l) => l.product_id.display_name === "TEST 2");
    expect(origTest.qty).toBe(3);
    expect(origTest2.qty).toBe(3);

    await Utils.clickControlButton("Split");
    await waitFor(".splitbill-screen");
    await Utils.clickSplitOrderline("TEST");
    await Utils.clickSplitOrderline("TEST 2");
    await Utils.clickSplitAction("Split");
    await animationFrame();

    const splitOrder2 = store.getOrder();
    expect(splitOrder2.lines.length).toBe(2);

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketOrder("001");
    await Utils.loadSelectedOrder();

    const finalOrder = store.getOrder();
    const finalTest = finalOrder.lines.find((l) => l.product_id.display_name === "TEST");
    const finalTest2 = finalOrder.lines.find((l) => l.product_id.display_name === "TEST 2");
    expect(finalTest.qty).toBe(2);
    expect(finalTest2.qty).toBe(2);
});

test("RefundStayCurrentTableTour: refund from another table stays on current table", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickPayButton();
    await Utils.clickPaymentMethod("Cash");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();

    await Utils.clickTable("4");
    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await contains(".ticket-screen .filter").click();
    await animationFrame();
    await contains('.dropdown-item:contains("Paid")').click();
    await animationFrame();
    await contains('.ticket-screen .order-row:contains("001")').click();
    await animationFrame();

    if (Utils.isMobile()) {
        await Utils.clickTicketReviewButton();
        Utils.sendBufferKeys("2");
        await animationFrame();
        await Utils.clickTicketAction("Refund");
    } else {
        await Utils.clickNumpad("2");
        await contains('.ticket-screen .pads button:contains("Refund")').click();
        await animationFrame();
    }

    const refundOrder = store.getOrder();
    expect(refundOrder.table_id.table_number).toBe(4);
    expect(refundOrder.lines.some((l) => l.qty < 0)).toBe(true);
});

test.timeout(10000);
test("PreparationPrinterContent: guest, notes, preset, note update in preparation data", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.setGuestCount(5);
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickControlButton("Customer Note");
    await waitFor(".modal textarea");
    await contains(".modal textarea").edit("Test customer note - orderline");
    await contains(".modal .btn-primary").click();
    await animationFrame();

    const order = store.getOrder();
    expect(order.getCustomerCount()).toBe(5);
    const line = order.lines[0];
    expect(line.getCustomerNote()).toBe("Test customer note - orderline");
    const changes = order.preparationChanges;
    expect(changes.quantity).toBe(1);
    expect(changes.addedQuantity.length).toBe(1);

    await Utils.clickOrderButton();
    await animationFrame();
    await Utils.clickPlanButton();
    await Utils.clickTable("1");
    await Utils.clickOrderline("TEST");
    await Utils.clickControlButton("Customer Note");
    await waitFor(".modal textarea");
    await contains(".modal textarea").edit("Updated customer note - orderline");
    await contains(".modal .btn-primary").click();
    await animationFrame();

    const updatedOrder = store.getOrder();
    const noteChanges = updatedOrder.preparationChanges;
    expect(noteChanges.noteUpdate || noteChanges.addedQuantity).not.toBe(undefined);

    await Utils.clickPlanButton();
    await Utils.clickTable("4");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickOrderline("TEST 2");
    await Utils.clickControlButton("Note");
    await waitFor(".modal");
    await contains(".modal .toggle-button").click();
    await animationFrame();
    await contains(".modal .btn-primary").click();
    await animationFrame();

    const order2 = store.getOrder();
    const changes2 = order2.preparationChanges;
    expect(changes2.quantity).toBe(1);

    await Utils.clickPlanButton();
    await Utils.clickTableById(3);
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickControlButton("In");

    const order3 = store.getOrder();
    expect(order3.preset_id.name).toBe("Out");
    const changes3 = order3.preparationChanges;
    expect(changes3.quantity).toBe(1);
});

test("test_preset_timing_restaurant: select takeaway preset, name popup, pick timing slot", async () => {
    mockDate("2025-06-15 10:00:00");

    const store = await setupAndMountPosApp({ set_tip_after_payment: false });
    store.models["pos.preset"].get(2).identification = "name";
    const att = store.models["resource.calendar.attendance"].create({
        hour_from: 0,
        hour_to: 24,
        dayofweek: "6",
    });
    const preset = store.models["pos.preset"].get(2);
    preset.attendance_ids = [...preset.attendance_ids, att];

    await contains(".floor-screen .new-order").click();
    await animationFrame();
    await Utils.clickDisplayedProduct("TEST");
    await Utils.selectPreset("Out");
    await animationFrame();
    await waitFor(".modal textarea");
    await contains(".modal textarea").edit("John");
    await Utils.confirmDialog();
    await animationFrame();
    await waitFor(".modal .preset-slot-button");

    expect(document.querySelector(".modal .btn-primary").textContent).toInclude("Today");

    const allSlots = document.querySelectorAll(".modal .preset-slot-button");
    const slotTexts = [...allSlots].map((el) => el.textContent.trim());
    expect(slotTexts.some((t) => t === "9:00")).toBe(false);
    await contains('.modal .preset-slot-button:contains("12:00")').click();
    await animationFrame();

    expect(document.querySelector(".pos-leftheader .preset-time-btn").textContent).toInclude(
        "12:00"
    );

    await Utils.clickPlanButton();
    await Utils.clickTable("4");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickOrders();
    await waitFor(".ticket-screen");

    const rows = document.querySelectorAll(".ticket-screen .order-row");
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toInclude("John");
    expect(rows[1].textContent).toInclude("002");
    if (!Utils.isMobile()) {
        expect(rows[0].textContent).toInclude("Out");
        expect(rows[1].textContent).toInclude("In");
    }

    await Utils.clickPlanButton();
    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickControlButton("In");
    await animationFrame();
    await waitFor(".modal .preset-slot-button");

    await contains('.modal button:contains("June 17")').click();
    await animationFrame();

    await contains('.modal .preset-slot-button:contains("12:00")').click();
    await animationFrame();

    await Utils.clickOrders();
    await waitFor(".ticket-screen");

    if (!Utils.isMobile()) {
        const allRows = document.querySelectorAll(".ticket-screen .order-row");
        expect(allRows[2].textContent).toInclude("06/17/2025");
    }
});

test("test_open_default_register_screen_config: starts on FloorScreen with tables mode", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    expect(store.router.state.current).toBe("FloorScreen");
    expect(document.querySelector(".floor-screen")).not.toBe(null);
});

test("test_show_default_with_register_screen: showDefault syncs selectedOrderUuid correctly", async () => {
    const store = await setupAndMountPosApp({
        default_screen: "register",
        set_tip_after_payment: false,
    });

    await contains(`.modal .selection-item:contains("In")`).click();
    await animationFrame();
    await Utils.clickDisplayedProduct("Accounting Test Product 1");
    await Utils.ensurePane("left");
    await contains(".product-screen .actionpad .set-table").click();
    await animationFrame();
    await Utils.sendBufferKeys("1");
    await contains(".product-screen .actionpad .assign-button").click();
    await animationFrame();
    await contains('.product-screen .actionpad button:contains("New")').click();
    await animationFrame();
    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketOrder("001");
    await Utils.loadSelectedOrder();

    expect(store.getOrder().lines.length).toBe(1);
    expect(store.getOrder().lines[0].product_id.display_name).toBe("Accounting Test Product 1");

    await Utils.ensurePane("left");
    await contains('.product-screen .actionpad button:contains("New")').click();
    await animationFrame();

    expect(store.getOrder().lines.length).toBe(0);
});

test("Full flow: select table, add product, pay with cash", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");

    const order = store.getOrder();
    expect(order.lines.length).toBe(1);

    await Utils.clickPayButton();
    await Utils.clickPaymentMethod("Cash");
    await Utils.clickValidatePayment();

    expect(order.state).toBe("paid");
    expect(store.router.state.current).toBe("FeedbackScreen");

    await Utils.clickNextOrder();

    expect(store.router.state.current).toBe("FloorScreen");
});

test("test_transfering_orders: create floating and table orders, verify 4 orders exist", async () => {
    await setupAndMountPosApp({ set_tip_after_payment: false });

    await contains(".floor-screen .new-order").click();
    await animationFrame();
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.ensurePane("left");
    await contains(".product-screen .new-tab").click();
    await waitFor(".modal");
    await contains(".modal textarea").edit("Cola");
    await contains(".modal .btn-primary").click();
    await animationFrame();
    await Utils.clickPlanButton();

    await contains(".floor-screen .new-order").click();
    await animationFrame();
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.ensurePane("left");
    await contains(".product-screen .new-tab").click();
    await waitFor(".modal");
    await contains(".modal textarea").edit("Water");
    await contains(".modal .btn-primary").click();
    await animationFrame();
    await Utils.clickPlanButton();

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPlanButton();

    await Utils.clickTable("4");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickPlanButton();

    await Utils.clickOrders();
    await waitFor(".ticket-screen");

    const orderRows = document.querySelectorAll(".ticket-screen .order-row");
    expect(orderRows.length).toBe(4);
});

test("test_guest_count_bank_payment: guest popup on open, add product, pay, go back", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });
    const defaultPreset = store.models["pos.preset"].get(1);
    defaultPreset.use_guest = true;

    await Utils.clickTable("1");
    await waitFor(".modal .numpad");
    await contains('.modal .numpad button:contains("5")').click();
    await animationFrame();
    await press("Enter");
    await animationFrame();
    await Utils.clickDisplayedProduct("TEST");

    expect(store.getOrder().getCustomerCount()).toBe(5);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await contains(".payment-screen .back-button").click();
    await animationFrame();

    expect(store.router.state.current).toBe("ProductScreen");
    expect(store.getOrder().getCustomerCount()).toBe(5);
});

test("test_customer_alone_saved: partner is preserved after leaving and reopening table", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickOrders();
    await Utils.clickRegister();
    await Utils.selectCustomer("Administrator");
    await Utils.checkSelectedCustomer("Administrator");

    await Utils.clickOrders();
    await Utils.clickRegister();
    expect(store.getOrder().partner_id.name).toBe("Administrator");
});

test.timeout(10000);
test("ControlButtonsTour: transfer, notes, guest count, cancel, cross-floor transfer", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPlanButton();

    await Utils.clickTable("4");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickTransferButton();
    await waitFor(".floor-screen");
    await Utils.clickTable("1");

    let order = store.getOrder();
    const testQty = order.lines
        .filter((l) => l.product_id.display_name === "TEST")
        .reduce((s, l) => s + l.qty, 0);
    const test2Qty = order.lines
        .filter((l) => l.product_id.display_name === "TEST 2")
        .reduce((s, l) => s + l.qty, 0);
    expect(testQty).toBe(6);
    expect(test2Qty).toBe(3);

    await Utils.clickControlButton("Split");
    await waitFor(".splitbill-screen");
    await contains(".splitbill-screen .button.back").click();
    await animationFrame();
    await contains('.orderline .product-name:contains("TEST"):first').click();
    await animationFrame();
    await Utils.clickControlButton("Note");
    await waitFor(".modal");
    await contains(".modal .toggle-button").click();
    await animationFrame();
    await contains(".modal .btn-primary").click();
    await animationFrame();

    await Utils.clickPlanButton();
    await Utils.clickTable("1");
    order = store.getOrder();
    const notedLine = order.lines.find((l) => l.product_id.display_name === "TEST" && l.note);
    expect(notedLine).not.toBe(undefined);

    await Utils.setGuestCount(15);
    expect(store.getOrder().getCustomerCount()).toBe(15);

    await Utils.clickControlButton("Guest");
    await waitFor(".modal .numpad");
    await contains('.modal .numpad button:contains("5")').click();
    await animationFrame();
    await press("Enter");
    await animationFrame();
    expect(store.getOrder().getCustomerCount()).toBe(5);

    await Utils.clickControlButton("Cancel Order");
    await waitFor(".modal");
    await Utils.confirmDialog();
    expect(store.router.state.current).toBe("FloorScreen");

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickTransferButton();
    await waitFor(".floor-screen");
    await Utils.clickFloor("Patio");
    await Utils.clickTableById(14);

    order = store.getOrder();
    expect(order.table_id.floor_id.name).toBe("Patio");
    const finalTestQty = order.lines
        .filter((l) => l.product_id.display_name === "TEST")
        .reduce((s, l) => s + l.qty, 0);
    expect(finalTestQty).toBe(5);
});

test("SplitBillScreenTour3: split partial qty, pay split, pay remainder", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickControlButton("Split");
    await waitFor(".splitbill-screen");
    await Utils.clickSplitOrderline("TEST");
    await Utils.clickSplitAction("Split");
    await animationFrame();

    expect(store.getOrder().lines.length).toBe(1);
    expect(store.getOrder().lines[0].qty).toBe(1);

    await Utils.clickPayButton();
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();

    const remainingOrder = store.getOrder();
    expect(remainingOrder.lines.length).toBe(1);
    expect(remainingOrder.lines[0].qty).toBe(1);

    await Utils.clickPayButton();
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();
});

test("SplitBillScreenTourPay: split selected items, pay split, pay remainder", async () => {
    await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("4");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickControlButton("Split");
    await waitFor(".splitbill-screen");
    await Utils.clickSplitOrderline("TEST");
    await Utils.clickSplitAction("Pay");
    await animationFrame();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();

    await Utils.clickSplitOrderline("TEST 2");
    await Utils.clickSplitAction("Pay");
    await animationFrame();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();
});

test("SplitBillScreenTour5Actions: split+transfer, split+pay, pay remainder", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickControlButton("Split");
    await waitFor(".splitbill-screen");
    await Utils.clickSplitOrderline("TEST");
    await Utils.clickSplitOrderline("TEST 2");
    await Utils.clickSplitAction("Transfer");
    await waitFor(".floor-screen");
    await Utils.clickTable("4");

    let order = store.getOrder();
    expect(order.lines.length).toBe(2);
    expect(order.lines.find((l) => l.product_id.display_name === "TEST").qty).toBe(1);
    expect(order.lines.find((l) => l.product_id.display_name === "TEST 2").qty).toBe(1);

    await Utils.clickPayButton();
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();

    await Utils.clickTable("1");
    order = store.getOrder();
    expect(order.lines.find((l) => l.product_id.display_name === "TEST").qty).toBe(1);

    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickControlButton("Split");
    await waitFor(".splitbill-screen");
    await Utils.clickSplitOrderline("TEST 2");
    await Utils.clickSplitOrderline("TEST");
    await Utils.clickSplitAction("Pay");
    await animationFrame();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();

    await Utils.clickSplitAction("Pay");
    await animationFrame();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();
});

test("test_pos_restaurant_default_course: course allocation by category across orders", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });
    store.config.use_course_allocation = true;
    store.config.iface_available_categ_ids = [1, 2];
    const cat1 = store.models["pos.category"].get(1);
    const cat2 = store.models["pos.category"].get(2);
    cat1.course_id = store.models["pos.course"].get(1);
    cat2.course_id = store.models["pos.course"].get(2);

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST 2");

    let order = store.getOrder();
    expect(order.courses.length).toBe(2);
    expect(order.courses[0].name).toBe("Default Course 1");
    expect(order.courses[1].name).toBe("Default Course 2");

    await Utils.clickDisplayedProduct("Multi Category Product");
    const multiLine = order.lines.at(-1);
    expect(multiLine.course_id.name).toBe("Default Course 1");

    await Utils.clickCourseButton();
    await Utils.clickDisplayedProduct("TEST");
    order = store.getOrder();
    expect(order.courses.length).toBe(2);

    await Utils.clickOrderButton();
    await animationFrame();
    await Utils.clickPlanButton();
    await Utils.clickTable("4");
    await Utils.clickDisplayedProduct("TEST");

    const order2 = store.getOrder();
    expect(order2.courses.length).toBe(1);
    expect(order2.courses[0].name).toBe("Default Course 1");

    await Utils.clickCourseButton();
    await Utils.clickDisplayedProduct("TEST 2");
});

test("test_course_restaurant_preparation_tour: 3 courses, fire sequentially, verify prep data", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickCourseButton();
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickCourseButton();
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickCourseButton();
    await Utils.clickDisplayedProduct("TEST");

    let order = store.getOrder();
    expect(order.courses.length).toBe(3);
    expect(order.courses[0].name).toBe("Course 1");
    expect(order.courses[1].name).toBe("Course 2");
    expect(order.courses[2].name).toBe("Course 3");

    const changes = order.preparationChanges;
    expect(changes.quantity).toBe(3);
    expect(changes.addedQuantity.length).toBe(3);

    await Utils.clickOrderButton();
    await animationFrame();
    await Utils.clickTable("1");
    order = store.getOrder();
    expect(order.preparationChanges.quantity).toBe(0);

    const fireBtn = document.querySelector(".actionpad .fire-btn");
    expect(fireBtn.textContent).toInclude("2");
    expect(fireBtn.classList.contains("btn-primary")).toBe(true);

    await Utils.clickFireCourseButton();
    await Utils.clickTable("1");

    const fireBtn2 = document.querySelector(".actionpad .fire-btn");
    expect(fireBtn2.textContent).toInclude("3");
    expect(fireBtn2.classList.contains("btn-primary")).toBe(true);

    await Utils.clickFireCourseButton();
    await Utils.clickTable("1");

    const badges = document.querySelectorAll(".order-course-name .text-bg-info");
    const firedBadges = [...badges].filter((b) => b.textContent.includes("Fired"));
    expect(firedBadges.length).toBe(3);

    expect(order.preparationChanges.quantity).toBe(0);
});

test("CategLabelCheck: order button shows category counts", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST 2");

    const order = store.getOrder();
    const catCount = order.preparationChanges.categoryCount;
    expect(catCount.length).toBeGreaterThan(0);
});

test("test_combo_preparation_receipt: combo parent above children, category counts, order count", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("Product combo");
    await waitFor(".modal label.combo-item");
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Wood chair"))'
    ).click();
    await animationFrame();
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Wood desk"))'
    ).click();
    await animationFrame();
    await contains(".modal footer button.confirm").click();
    await animationFrame();

    await Utils.clickDisplayedProduct("Product combo");
    await waitFor(".modal label.combo-item");
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Steel chair"))'
    ).click();
    await animationFrame();
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Steel desk"))'
    ).click();
    await animationFrame();
    await contains(".modal footer button.confirm").click();
    await animationFrame();

    const order = store.getOrder();
    const catCount = order.preparationChanges.categoryCount;
    expect(catCount.length).toBeGreaterThan(0);
    const totalCount = catCount.reduce((sum, c) => sum + c.count, 0);
    expect(totalCount).toBe(4);

    await Utils.clickPlanButton();
    await Utils.clickTable("1");

    const changes = order.preparationChanges;
    const addedLines = changes.addedQuantity;
    expect(addedLines.length).toBe(6);

    const names = addedLines.map(
        (l) => store.models["product.product"].get(l.data.product_id)?.display_name
    );
    expect(names[0]).toBe("Product combo");
    expect(names[1]).toBe("Wood chair");
    expect(names[2]).toBe("Wood desk");
    expect(names[3]).toBe("Product combo");
    expect(names[4]).toBe("Steel chair");
    expect(names[5]).toBe("Steel desk");

    for (const line of addedLines) {
        if (line.data.combo_parent_uuid) {
            const parentIdx = addedLines.findIndex((l) => l.uuid === line.data.combo_parent_uuid);
            const childIdx = addedLines.indexOf(line);
            expect(parentIdx).toBeLessThan(childIdx);
        }
    }
});

test("MultiPreparationPrinter: only printer with matching category prints, no empty receipt", async () => {
    const store = await setupAndMountPosApp({
        use_order_printer: true,
        set_tip_after_payment: false,
    });
    store.models["pos.printer"].create({
        name: "Printer 1",
        printer_type: "epson_epos",
        use_type: "preparation",
        product_categories_ids: [store.models["pos.category"].get(2)],
    });
    store.models["pos.printer"].create({
        name: "Printer 2",
        printer_type: "epson_epos",
        use_type: "preparation",
        product_categories_ids: [store.models["pos.category"].get(1)],
    });
    store.config.preparation_printer_ids = store.models["pos.printer"].filter(
        (p) => p.use_type === "preparation"
    );

    await store.ticketPrinter.initPrinters();
    store.ticketPrinter.generateIframe = async () => ({
        contentWindow: {},
        contentDocument: { body: { innerHTML: "" } },
        style: {},
    });
    store.ticketPrinter.setIframeSizeFromPrinter = () => {};
    store.ticketPrinter.generateImage = async () => "mock-image";

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickOrderButton();
    await animationFrame();
    await waitFor(".modal");

    const errorBody = document.querySelector(".modal-body")?.textContent || "";
    expect(errorBody.includes("Printer 2")).toBe(true);
    expect(errorBody.includes("Printer 1")).not.toBe(true);

    await Utils.confirmDialog();
});

test("test_name_preset_skip_screen: partner set skips name popup, pay succeeds", async () => {
    const store = await setupAndMountPosApp({
        use_presets: true,
        set_tip_after_payment: false,
    });
    const takeawayPreset = store.models["pos.preset"].get(3);
    store.config.default_preset_id = takeawayPreset;
    store.config.available_preset_ids = [takeawayPreset];

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.selectCustomer("Administrator");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Cash");
    await Utils.clickValidatePayment();
    await waitFor(".feedback-screen");
    await Utils.clickNextOrder();

    expect(store.router.state.current).toBe("FloorScreen");
});

test("test_preset_delivery_restaurant: cancel order with preset returns to floor", async () => {
    const store = await setupAndMountPosApp({
        use_presets: true,
        set_tip_after_payment: false,
    });
    const deliveryPreset = store.models["pos.preset"].get(4);
    store.config.default_preset_id = deliveryPreset;
    store.config.available_preset_ids = [
        store.models["pos.preset"].get(2),
        store.models["pos.preset"].get(1),
        deliveryPreset,
    ];
    const partner = store.models["res.partner"].get(3);
    partner.street = "123 Main St";
    partner.city = "Brussels";
    partner.zip = "1000";
    partner.country_id = store.models["res.country"].get(1);

    await Utils.clickTable("1");
    await Utils.selectCustomer("Administrator");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickControlButton("Cancel Order");
    await waitFor(".modal");
    await contains(".modal .btn-secondary").click();
    await animationFrame();

    expect(store.router.state.current).toBe("ProductScreen");

    await Utils.clickControlButton("Cancel Order");
    await waitFor(".modal");
    await Utils.confirmDialog();

    expect(store.router.state.current).toBe("FloorScreen");
});

test("test_open_register_with_preset_takeaway: timing popup on table, cancel removes order", async () => {
    mockDate("2025-06-15 10:00:00");

    const store = await setupAndMountPosApp({ set_tip_after_payment: false });
    const att = store.models["resource.calendar.attendance"].create({
        hour_from: 0,
        hour_to: 24,
        dayofweek: "6",
    });
    const preset = store.models["pos.preset"].get(2);
    preset.attendance_ids = [...preset.attendance_ids, att];
    store.config.default_preset_id = preset;

    await Utils.clickTable("1");
    await waitFor(".modal .preset-slot-button");

    expect(document.querySelector(".modal .btn-primary").textContent).toInclude("Today");
    const allSlots = document.querySelectorAll(".modal .preset-slot-button");
    const slotTexts = [...allSlots].map((el) => el.textContent.trim());
    expect(slotTexts.some((t) => t == "9:00")).toBe(false);

    await contains('.modal .preset-slot-button:contains("12:20")').click();
    await animationFrame();

    expect(document.querySelector(".pos-leftheader .preset-time-btn").textContent).toInclude(
        "12:20"
    );

    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickControlButton("Cancel Order");
    await waitFor(".modal");
    await contains(".modal .btn-secondary").click();
    await animationFrame();
    await Utils.clickControlButton("Cancel Order");
    await waitFor(".modal");
    await Utils.confirmDialog();

    expect(store.router.state.current).toBe("FloorScreen");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");

    const orderRows = document.querySelectorAll(".ticket-screen .order-row");
    expect(orderRows.length).toBe(0);
});

test("RestaurantPresetEatInTour: eat-in table order, pay, receipt has no preset info", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("4");
    await Utils.clickDisplayedProduct("TEST");

    expect(store.getOrder().preset_id.name).toBe("In");

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Cash");
    await Utils.clickValidatePayment();
    await waitFor(".feedback-screen");

    expect(store.router.state.current).toBe("FeedbackScreen");
    expect(document.querySelector(".feedback-screen .preset-info")).toBe(null);

    await Utils.clickNextOrder();

    expect(store.router.state.current).toBe("FloorScreen");
});

test("test_combo_apply_after_preparation: apply combo groups standalone lines, persists after reload", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("Wood chair");
    await Utils.clickDisplayedProduct("Wood desk");
    await Utils.clickPlanButton();
    await Utils.clickTable("1");
    await Utils.ensurePane("left");
    await contains('.combo-proposition button:contains("Apply")').click();
    await animationFrame();
    await Utils.confirmDialog();

    const order = store.getOrder();
    const comboParent = order.lines.find(
        (l) => l.product_id.display_name === "Product combo" || l.combo_line_ids?.length > 0
    );
    expect(comboParent).not.toBe(undefined);
    const standaloneChair = order.lines.find(
        (l) => l.product_id.display_name === "Wood chair" && !l.combo_parent_id
    );
    expect(standaloneChair).toBe(undefined);

    await Utils.clickPlanButton();
    await Utils.clickTable("1");

    const orderAfter = store.getOrder();
    const comboParentAfter = orderAfter.lines.find(
        (l) => l.product_id.display_name === "Product combo" || l.combo_line_ids?.length > 0
    );
    expect(comboParentAfter).not.toBe(undefined);
    const standaloneAfter = orderAfter.lines.find(
        (l) => l.product_id.display_name === "Wood chair" && !l.combo_parent_id
    );
    expect(standaloneAfter).toBe(undefined);
});

test("test_multiple_preparation_printer_different_categories: both printers triggered, then pay without warning", async () => {
    const store = await setupAndMountPosApp({
        use_order_printer: true,
        set_tip_after_payment: false,
    });
    store.models["pos.printer"].create({
        name: "Printer 1",
        printer_type: "epson_epos",
        use_type: "preparation",
        product_categories_ids: [store.models["pos.category"].get(2)],
    });
    store.models["pos.printer"].create({
        name: "Printer 2",
        printer_type: "epson_epos",
        use_type: "preparation",
        product_categories_ids: [store.models["pos.category"].get(1)],
    });
    store.config.preparation_printer_ids = store.models["pos.printer"].filter(
        (p) => p.use_type === "preparation"
    );

    await store.ticketPrinter.initPrinters();
    store.ticketPrinter.generateIframe = async () => ({
        contentWindow: {},
        contentDocument: { body: { innerHTML: "" } },
        style: {},
    });
    store.ticketPrinter.setIframeSizeFromPrinter = () => {};
    store.ticketPrinter.generateImage = async () => "mock-image";

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickOrderButton();
    await animationFrame();
    await waitFor(".modal");

    const errorBody = document.querySelector(".modal-body")?.textContent || "";
    expect(errorBody.includes("Printer 1: The printer is not reachable")).toBe(true);
    expect(errorBody.includes("Printer 2: The printer is not reachable")).toBe(true);

    await Utils.confirmDialog();
    await Utils.clickTable("1");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();

    expect(store.router.state.current).toBe("FeedbackScreen");
});

test("test_combo_synchronisation: combo links persist after partner change, course transfer moves entire combo", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("Product combo");
    await waitFor(".modal label.combo-item");
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Wood chair"))'
    ).click();
    await animationFrame();
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Wood desk"))'
    ).click();
    await animationFrame();
    await contains(".modal footer button.confirm").click();
    await animationFrame();

    await Utils.clickPlanButton();
    await Utils.clickTable("1");
    await Utils.selectCustomer("Administrator");
    await Utils.clickPlanButton();
    await Utils.clickTable("1");

    expect(document.querySelector(".orderline-combo")).not.toBe(null);

    await Utils.clickControlButton("Course");
    await animationFrame();
    const comboChild = Utils.queryEl(".orderline .product-name", "Wood chair");
    await contains(comboChild).click();
    await animationFrame();
    await Utils.clickControlButton("Transfer course");
    await waitFor(".modal");
    const courseBtn = Utils.queryEl(".modal-body button", "Course 2");
    await contains(courseBtn).click();
    await animationFrame();

    const order = store.getOrder();
    const comboLines = order.lines.filter((l) => l.combo_parent_id || l.combo_line_ids?.length > 0);
    const allSameCourse = comboLines.every(
        (l) => l.course_id?.name === comboLines[0].course_id?.name
    );
    expect(allSameCourse).toBe(true);
});

test("test_combo_preparation_receipt_layout: combo parent above children in receipt", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("Product combo");
    await waitFor(".modal label.combo-item");
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Wood chair"))'
    ).click();
    await animationFrame();
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Wood desk"))'
    ).click();
    await animationFrame();
    await contains(".modal footer button.confirm").click();
    await animationFrame();

    const order = store.getOrder();
    const changes = order.preparationChanges;
    const addedLines = changes.addedQuantity;
    expect(addedLines.length).toBe(3);

    const names = addedLines.map(
        (l) => store.models["product.product"].get(l.data.product_id)?.display_name || l.data.name
    );
    const parentIdx = names.findIndex((n) => n === "Product combo");
    const child1Idx = names.findIndex((n) => n === "Wood chair");
    const child2Idx = names.findIndex((n) => n === "Wood desk");
    expect(parentIdx).toBe(0);
    expect(child1Idx).toBe(1);
    expect(child2Idx).toBe(2);
});

test("SplitBillScreenTour4ProductCombo: split combos as group, pay, verify remainder", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("Product combo");
    await waitFor(".modal label.combo-item");
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Wood chair"))'
    ).click();
    await animationFrame();
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Wood desk"))'
    ).click();
    await animationFrame();
    await contains(".modal footer button.confirm").click();
    await animationFrame();

    await Utils.clickDisplayedProduct("Product combo");
    await waitFor(".modal label.combo-item");
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Steel chair"))'
    ).click();
    await animationFrame();
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Steel desk"))'
    ).click();
    await animationFrame();
    await contains(".modal footer button.confirm").click();
    await animationFrame();

    await Utils.ensurePane("left");
    await contains('.orderline .product-name:contains("Steel chair")').click();
    await animationFrame();
    await Utils.clickNumpad("2");
    await Utils.ensurePane("right");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickDisplayedProduct("TEST 2");
    await Utils.clickControlButton("Split");
    await waitFor(".splitbill-screen");
    await Utils.clickSplitOrderline("TEST");
    await Utils.clickSplitOrderline("Wood chair");
    await Utils.clickSplitOrderline("Steel chair");
    await Utils.clickSplitAction("Split");
    await animationFrame();

    const splitOrder = store.getOrder();
    expect(splitOrder.lines.length).toBeGreaterThan(0);

    await Utils.clickPayButton();
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();

    const remainingOrder = store.getOrder();
    expect(remainingOrder.lines.some((l) => l.product_id.display_name === "TEST 2")).toBe(true);
});

test("FloorScreenTour: mounted FloorScreen switches floors, opens a table, and adds a floor", async () => {
    const store = await setupFloorTest();
    const screen = await mountFloorScreen(store);

    const activeFloor = queryOne(".floor-selector .button-floor.active");
    expect(activeFloor.textContent.trim()).toBe("Main Floor");
    expect(getVisibleTableNumbers()).toInclude("1");
    expect(getVisibleTableNumbers()).toInclude("2");
    expect(getVisibleTableNumbers()).toInclude("4");

    await contains(".floor-selector .button-floor:contains(Patio)").click();
    expect(queryOne(".floor-selector .button-floor.active").textContent.trim()).toBe("Patio");
    expect(getVisibleTableNumbers()).toInclude("101");
    expect(getVisibleTableNumbers()).toInclude("102");
    expect(getVisibleTableNumbers()).toInclude("103");

    if (Utils.isMobile()) {
        screen.startFloorPlanEditing();
        await animationFrame();
    } else {
        await contains(".edit-plan").click();
    }
    expect(store.floorPlan.editMode).toBe(true);

    await contains(".toolbar-floor-selector").click();
    await contains(".toolbar-floor-selector-item:contains(Add Floor)").click();
    expect(queryOne(".modal-title").textContent.trim()).toBe("New Floor");
    queryOne(".modal-body textarea").focus();
    await edit("Test Floor");
    await animationFrame();
    await contains(".modal-footer button.btn-primary").click();
    await tick();
    await animationFrame();

    expect(store.floorPlan.floors.some((f) => f.name === "Test Floor")).toBe(true);
    expect(store.floorPlan.selectedFloor.name).toBe("Test Floor");
    expect(queryOne(".toolbar-floor-selector").textContent.trim()).toBe("Test Floor");
});

test("Full flow: mount PosApp, return to the same floor, select table, add product, pay with cash", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await contains(".floor-selector .button-floor:contains(Patio)").click();
    await contains(".o_fp_table[data-table_id='14']").click();
    expect(store.router.state.current).toBe("ProductScreen");
    expect(store.getOrder().table_id.id).toBe(14);

    await Utils.clickPlanButton();
    expect(store.router.state.current).toBe("FloorScreen");
    expect(queryOne(".floor-selector .button-floor.active").textContent.trim()).toBe("Patio");

    await contains(".o_fp_table[data-table_id='14']").click();
    expect(store.router.state.current).toBe("ProductScreen");

    await Utils.clickDisplayedProduct("TEST");
    const order = store.getOrder();
    expect(order.table_id.id).toBe(14);
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].product_id.product_tmpl_id.id).toBe(5);

    await Utils.clickPayButton();
    await Utils.clickPaymentMethod("Cash");
    expect(order.payment_ids).toHaveLength(1);

    await Utils.clickValidatePayment();
    expect(order.state).toBe("paid");
    expect(store.router.state.current).toBe("FeedbackScreen");

    await contains(".feedback-screen .validation").click();
    await animationFrame();
    expect(store.router.state.current).toBe("FloorScreen");
});

test("test_add_new_table_number_with_multi_floor: table numbers increment per floor", async () => {
    const store = await setupFloorTest();
    const screen = await mountFloorScreen(store);

    if (Utils.isMobile()) {
        screen.startFloorPlanEditing();
        await animationFrame();
    } else {
        await contains(".edit-plan").click();
    }

    const floorPlan = store.floorPlan;
    expect(floorPlan.editMode).toBe(true);

    const mainFloor = floorPlan.floors.find((f) => f.name === "Main Floor");
    floorPlan.selectFloorByUuid(mainFloor.uuid);
    const newMainTable = floorPlan.addTable("square");
    expect(newMainTable.tableNumber).toBe(mainFloor.getMaxTableNumber());
    expect(floorPlan.selectedFloor.name).toBe("Main Floor");

    const patioFloor = floorPlan.floors.find((f) => f.name === "Patio");
    floorPlan.selectFloorByUuid(patioFloor.uuid);
    const newPatioTable = floorPlan.addTable("square");
    expect(newPatioTable.tableNumber).toBe(patioFloor.getMaxTableNumber());
    expect(floorPlan.selectedFloor.name).toBe("Patio");
});

test("PosResTicketScreenTour: delete order and table becomes empty", async () => {
    const store = await setupAndMountPosApp({ set_tip_after_payment: false });

    await Utils.clickTable("1");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPlanButton();
    await Utils.clickOrders();
    await waitFor(".ticket-screen");

    if (Utils.isMobile()) {
        await contains('.ticket-screen .order-row:contains("001")').click();
        await animationFrame();
    }
    await contains('.ticket-screen .order-row:contains("001") .fa-trash').click();
    await animationFrame();
    await Utils.confirmDialog();
    await Utils.clickPlanButton();
    await Utils.clickTable("1");

    expect(store.getOrder().lines.length).toBe(0);
});

test("test_tip_after_payment: tip adjusts payment line based on remaining/change", async () => {
    const store = await setupAndMountPosApp({
        iface_tipproduct: true,
        set_tip_after_payment: false,
    });
    const tipProduct = store.models["product.product"].get(1);
    store.config.tip_product_id = tipProduct;
    const tmpl = store.models["product.template"].create({
        name: "Minute Maid",
        display_name: "Minute Maid",
        list_price: 3,
        taxes_id: [],
        available_in_pos: true,
        pos_categ_ids: [store.models["pos.category"].get(1)],
    });
    store.models["product.product"].create({
        display_name: "Minute Maid",
        lst_price: 3,
        pos_categ_ids: [store.models["pos.category"].get(1)],
        product_tmpl_id: tmpl,
    });
    const bankPm = store.models["pos.payment.method"].create({
        name: "Bank",
        is_cash_count: false,
        type: "bank",
        payment_method_type: "none",
    });
    store.config.payment_method_ids = [...store.config.payment_method_ids, bankPm];

    await Utils.clickTable("2");
    await Utils.clickDisplayedProduct("TEST");

    const order = store.getOrder();
    expect(order.lines.length).toBe(1);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    await Utils.clickPaymentMethod("Bank");
    await animationFrame();
    await Utils.sendBufferKeys("1");

    await contains(".payment-screen .button:contains('Tip')").click();
    await animationFrame();
    await waitFor(".modal .numpad");
    await contains('.modal .numpad button:contains("1")').click();
    await animationFrame();
    await press("Enter");
    await animationFrame();

    expect(document.querySelector(".paymentline.selected .payment-name").textContent).toInclude(
        "Bank"
    );
    expect(
        document.querySelector(".paymentline.selected .payment-amount").textContent.includes("2.00")
    ).toBe(true);

    await Utils.clickPaymentMethod("Bank");
    await animationFrame();
    expect(document.querySelector(".paymentline.selected .payment-name").textContent).toInclude(
        "Bank"
    );
    expect(
        document.querySelector(".paymentline.selected .payment-amount").textContent.includes("2.45")
    ).toBe(true);

    const lines1 = document.querySelectorAll(".paymentlines .paymentline");
    expect(lines1.length).toBe(2);
    expect(lines1[0].textContent).toInclude("2.00");
    expect(lines1[1].classList.contains("selected")).toBe(true);
    expect(lines1[1].textContent).toInclude("2.45");

    await contains(
        '.paymentlines .paymentline .payment-infos:has(.payment-name:contains("Bank")):has(.payment-amount:contains("2.00")) ~ .delete-button'
    ).click();
    await animationFrame();

    const lines2 = document.querySelectorAll(".paymentlines .paymentline");
    expect(lines2.length).toBe(1);
    expect(lines2[0].classList.contains("selected")).toBe(true);
    expect(lines2[0].textContent.includes("2.45")).toBe(true);

    await Utils.sendBufferKeys("5");
    const lines3 = document.querySelectorAll(".paymentlines .paymentline");
    expect(lines3.length).toBe(1);
    expect(lines3[0].textContent).toInclude("5.00");

    await contains(".payment-screen .button:contains('Tip')").click();
    await animationFrame();
    await waitFor(".modal .numpad");
    await contains('.modal .numpad button:contains("2")').click();
    await animationFrame();
    await press("Enter");
    await animationFrame();

    const lines4 = document.querySelectorAll(".paymentlines .paymentline");
    expect(lines4.length).toBe(1);

    await Utils.clickPaymentMethod("Bank");
    await animationFrame();

    const lines5 = document.querySelectorAll(".paymentlines .paymentline");
    expect(lines5.length).toBe(2);
    expect(lines5[0].textContent.includes("5.45")).toBe(true);
    expect(lines5[1].classList.contains("selected")).toBe(true);
    expect(lines5[1].textContent).toInclude("0.00");

    await contains(
        '.paymentlines .paymentline .payment-infos:has(.payment-name:contains("Bank")):has(.payment-amount:contains("5.45")) ~ .delete-button'
    ).click();
    await animationFrame();

    const lines6 = document.querySelectorAll(".paymentlines .paymentline");
    expect(lines6.length).toBe(1);
    expect(lines6[0].textContent).toInclude("0.00");

    await Utils.sendBufferKeys("5");
    await contains(".payment-screen .button:contains('Tip')").click();
    await animationFrame();
    await waitFor(".modal .numpad");
    await contains('.modal .numpad button:contains("3")').click();
    await animationFrame();
    await press("Enter");
    await animationFrame();

    expect(document.querySelector(".paymentline.selected .payment-name").textContent).toInclude(
        "Bank"
    );
    expect(document.querySelector(".paymentline.selected .payment-amount").textContent).toInclude(
        "6.00"
    );
});
