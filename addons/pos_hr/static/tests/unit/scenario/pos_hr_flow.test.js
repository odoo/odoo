import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { createTestProduct } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as HrUiUtils from "@pos_hr/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...HrUiUtils };

definePosModels();

test("PosHrTour: wrong pin, cashier rights and per-employee orders", async () => {
    const store = await Utils.setupAndMountPosHrApp();
    createTestProduct(store, { id: 9100, name: "Untaxed Product", price: 100, taxes_id: [] });

    expect(Utils.loginScreenIsShown()).toBe(true);
    await Utils.clickOpenRegister();
    expect(Utils.loginScreenIsShown()).toBe(true);

    await Utils.clickLoginButton();
    expect(Utils.cashierSelectionHas("Administrator")).toBe(true);
    expect(Utils.cashierSelectionHas("Employee1")).toBe(true);
    expect(Utils.cashierSelectionHas("Employee2")).toBe(true);

    await Utils.selectCashierInPopup("Employee2");
    await waitFor(".modal .pos-number-popup");
    await Utils.enterPinDigits("56");
    expect(Utils.pinPopupValue()).toBe("••");
    await Utils.enterPinDigits("70");
    expect(Utils.pinPopupValue()).toBe("••••");
    await Utils.confirmPinPopup();

    expect(Utils.loginScreenIsShown()).toBe(true);
    expect(store.getCashier()).toBeEmpty();

    await Utils.login("Employee2", "5678");
    await waitFor(".product-screen");
    expect(store.getCashier().name).toBe("Employee2");

    await Utils.switchCashier("Administrator", "1234");
    await waitFor(".product-screen");
    expect(store.getCashier().name).toBe("Administrator");
    await Utils.openMenu();
    expect(Utils.hasMenuOption("Create Product")).toBe(true);
    await Utils.closeMenu();

    await Utils.switchCashier("Employee1");
    await waitFor(".product-screen");
    expect(store.getCashier().name).toBe("Employee1");
    await Utils.openMenu();
    expect(Utils.hasMenuOption("Create Product")).toBe(false);
    await Utils.closeMenu();

    await Utils.clickDisplayedProduct("TEST");
    expect(store.getOrder().employee_id.name).toBe("Employee1");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    if (!Utils.isMobile()) {
        expect(Utils.ticketRowContains(1, "Employee1")).toBe(true);
    }
    await Utils.clickRegister();
    await waitFor(".product-screen");

    await Utils.clickLockButton();
    expect(Utils.loginScreenIsShown()).toBe(true);
    await Utils.login("Employee2", "5678");
    await waitFor(".product-screen");

    await Utils.createFloatingOrder();
    await Utils.clickDisplayedProduct("TEST");
    expect(store.getOrder().employee_id.name).toBe("Employee2");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    if (!Utils.isMobile()) {
        expect(Utils.ticketRowContains(1, "Employee1")).toBe(true);
        expect(Utils.ticketRowContains(2, "Employee2")).toBe(true);
    }
    await Utils.clickRegister();
    await waitFor(".product-screen");

    await Utils.openMenu();
    expect(Utils.hasMenuOption("Cash In/Out")).toBe(true);
    await Utils.clickMenuOption("Cash In/Out");
    await waitFor(".modal");
    await Utils.cancelDialog();

    await Utils.switchCashier("Administrator", "1234");
    await waitFor(".product-screen");
    await Utils.createFloatingOrder();
    await Utils.clickDisplayedProduct("Untaxed Product");
    await Utils.clickNumpadButtons("Price", 8, "Qty");
    expect(store.getOrder().lines[0].price_unit).toBe(8);
    expect(Utils.getOrderTotal()).toInclude("8.00");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    if (!Utils.isMobile()) {
        expect(Utils.ticketRowContains(1, "Employee1")).toBe(true);
        expect(Utils.ticketRowContains(2, "Employee2")).toBe(true);
        expect(Utils.ticketRowContains(3, "Administrator")).toBe(true);
    }
    await Utils.clickRegister();
    await waitFor(".product-screen");

    await Utils.openMenu();
    expect(Utils.hasMenuOption("Close Register")).toBe(true);
    await Utils.clickMenuOption("Close Register");
    await waitFor(".modal .close-pos-popup");
    expect(document.querySelector(".modal .modal-header").textContent).toInclude(
        "Closing Register"
    );
});

test("CashierCanSeeProductInfo: product info opens and closes for the admin cashier", async () => {
    const store = await Utils.setupAndMountPosHrApp();

    await Utils.login("Administrator", "1234");
    await waitFor(".product-screen");
    expect(store.getCashier().name).toBe("Administrator");

    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickControlButton("Info");
    await waitFor(".modal .product-info-popup");

    await contains('.modal .btn-primary:contains("Close")').click();
    await animationFrame();
    expect(".modal").toHaveCount(0);
});

test("CashierCannotClose: only a manager gets the Close Register option", async () => {
    const store = await Utils.setupAndMountPosHrApp();

    await Utils.login("Employee2", "5678");
    await waitFor(".product-screen");
    expect(store.employeeIsAdmin).toBe(false);

    await Utils.openMenu();
    expect(Utils.hasMenuOption("Close Register")).toBe(false);
    await Utils.closeMenu();

    await Utils.switchCashier("Administrator", "1234");
    await waitFor(".product-screen");
    await Utils.openMenu();
    expect(Utils.hasMenuOption("Close Register")).toBe(true);
});

test("test_basic_user_can_change_price: unrestricted price control lets a basic cashier set a price", async () => {
    const store = await Utils.setupAndMountPosHrApp({ restrict_price_control: false });
    createTestProduct(store, { id: 9100, name: "Untaxed Product", price: 100, taxes_id: [] });

    await Utils.login("Employee2", "5678");
    await waitFor(".product-screen");
    expect(store.cashierHasPriceControlRights()).toBe(true);

    await Utils.clickDisplayedProduct("Untaxed Product");
    await Utils.clickNumpadButtons("Price", 10, "Qty");
    expect(store.getOrder().lines[0].price_unit).toBe(10);
    expect(Utils.getOrderTotal()).toInclude("10.00");
    expect(".modal").toHaveCount(0);
});

test("test_basic_user_cannot_change_price: restricted price control blocks a basic cashier", async () => {
    const store = await Utils.setupAndMountPosHrApp({ restrict_price_control: true });
    createTestProduct(store, { id: 9100, name: "Untaxed Product", price: 100, taxes_id: [] });

    await Utils.login("Employee2", "5678");
    await waitFor(".product-screen");
    expect(store.cashierHasPriceControlRights()).toBe(false);

    await Utils.clickDisplayedProduct("Untaxed Product");
    const priceBefore = store.getOrder().lines[0].price_unit;
    await Utils.clickNumpadButtons("Price", 10, "Qty");
    expect(store.getOrder().lines[0].price_unit).toBe(priceBefore);
});

test("test_minimal_employee_refund: refund pads are hidden for a minimal employee", async () => {
    const store = await Utils.setupAndMountPosHrApp();

    await Utils.login("Administrator", "1234");
    await waitFor(".product-screen");
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await waitFor(".feedback-screen");
    await Utils.clickNextOrder();
    await waitFor(".product-screen");

    await Utils.switchCashier("A Little Guy");
    await waitFor(".product-screen");
    expect(store.getCashier()._role).toBe("minimal");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketFilter("Paid");
    await Utils.selectTicketOrder("001");
    await Utils.ensureTicketPane("right");
    expect(".ticket-screen .subpads").toHaveCount(0);

    await Utils.clickRegister();
    await waitFor(".product-screen");
    await Utils.switchCashier("Administrator", "1234");
    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketFilter("Paid");
    await Utils.selectTicketOrder("001");
    await Utils.ensureTicketPane("right");
    expect(".ticket-screen .subpads").toHaveCount(1);
});

test("test_cost_and_margin_visibility: financials hidden only for a minimal employee", async () => {
    const store = await Utils.setupAndMountPosHrApp({
        is_margins_costs_accessible_to_every_user: true,
    });

    await Utils.login("Administrator", "1234");
    await waitFor(".product-screen");
    await Utils.clickDisplayedProduct("TEST");

    await Utils.clickControlButton("Info");
    await waitFor(".modal .product-info-popup");
    expect(".modal .financials-order").toHaveCount(1);
    await contains('.modal .btn-primary:contains("Close")').click();
    await animationFrame();

    await Utils.switchCashier("Employee2", "5678");
    await Utils.selectOrderlineIfNeeded(store, "TEST");
    await Utils.clickControlButton("Info");
    await waitFor(".modal .product-info-popup");
    expect(".modal .financials-order").toHaveCount(1);
    await contains('.modal .btn-primary:contains("Close")').click();
    await animationFrame();

    await Utils.switchCashier("A Little Guy");
    expect(store.getCashier()._role).toBe("minimal");
    await Utils.selectOrderlineIfNeeded(store, "TEST");
    await Utils.clickControlButton("Info");
    await waitFor(".modal .product-info-popup");
    expect(".modal .financials-order").toHaveCount(0);
});

test("test_scan_employee_barcode_with_pos_hr_disabled: scanning a cashier badge is a no-op", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await Utils.setupAndMountPosHrApp({ module_pos_hr: false });

    await Utils.clickOpenRegister();
    await waitFor(".product-screen");

    await Utils.scanBarcode("041123");
    await waitFor(".product-screen");
    expect(store.getOrder().lines).toHaveLength(0);
});

test("test_switch_cashier_with_badge: scanning a badge switches the cashier", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await Utils.setupAndMountPosHrApp();

    expect(Utils.loginScreenIsShown()).toBe(true);
    await Utils.scanBarcode("041222");
    await Utils.enterPin("5678");
    await waitFor(".product-screen");
    expect(store.getCashier().name).toBe("Employee2");

    await Utils.clickDisplayedProduct("TEST");
    expect(store.getOrder().employee_id.name).toBe("Employee2");

    if (Utils.isMobile()) {
        await Utils.switchCashier("A Little Guy");
    } else {
        await Utils.scanBarcode("041333");
    }
    expect(store.getCashier().name).toBe("A Little Guy");

    await Utils.createFloatingOrder();
    await Utils.clickDisplayedProduct("TEST");
    expect(store.getOrder().employee_id.name).toBe("A Little Guy");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    if (!Utils.isMobile()) {
        expect(Utils.ticketRowContains(1, "Employee2")).toBe(true);
        expect(Utils.ticketRowContains(2, "A Little Guy")).toBe(true);
    }
});
