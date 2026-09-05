import { animationFrame, press, queryAll, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { clickOrderline, isMobile, mountPosApp } from "@point_of_sale/../tests/unit/ui_utils";

export async function setupAndMountPosHrApp(config = {}) {
    const store = await setupPosEnv();
    Object.assign(store.config, {
        preparation_printer_ids: [],
        receipt_printer_ids: [],
        ...config,
    });
    store.resetCashier();
    store.hasLoggedIn = false;
    store.navigate("LoginScreen");
    await mountPosApp(store);
    return store;
}

export function loginScreenIsShown() {
    return document.querySelector(".login-overlay .screen-login") !== null;
}

export async function clickOpenRegister() {
    await contains(".login-overlay .open-register-btn").click();
    await animationFrame();
}

export async function clickLoginButton() {
    if (!document.querySelector(".login-overlay .select-cashier")) {
        await clickOpenRegister();
    }
    await contains(".login-overlay .select-cashier").click();
    await animationFrame();
    await waitFor(".modal");
}

export async function clickCashierName() {
    await contains(".cashier-name").click();
    await animationFrame();
    await waitFor(".modal");
}

// Small screens get a "Lock" burger entry instead of the navbar lock button.
export async function clickLockButton() {
    if (isMobile()) {
        await openMenu();
        await clickMenuOption("Lock");
        return;
    }
    await contains(".pos-rightheader .lock-screen").click();
    await animationFrame();
}

export function cashierSelectionNames() {
    return queryAll(".modal .cashier-selection-item").map((el) => el.textContent.trim());
}

export function cashierSelectionHas(name) {
    return cashierSelectionNames().some((text) => text.includes(name));
}

export async function selectCashierInPopup(name) {
    const item = queryAll(".modal .cashier-selection-item").find((el) =>
        el.textContent.includes(name)
    );
    await contains(item).click();
    await animationFrame();
}

export function pinPopupValue() {
    const el = document.querySelector(".modal .popup-input .input-value");
    return el ? el.textContent.trim() : "";
}

export async function enterPinDigits(pin) {
    for (const digit of pin.toString().split("")) {
        await contains(`.modal .numpad button:contains("${digit}")`).click();
        await animationFrame();
    }
}

// web's dialog.scss hides `o-default-button:not(:only-child)`, and that stylesheet is part of
// the unit test bundle even though the POS bundle drops it. The NumberPopup footer buttons are
// therefore not clickable here, so go through the popup's own "enter" hotkey instead.
export async function confirmPinPopup() {
    await press("Enter");
    await animationFrame();
}

export async function enterPin(pin) {
    await waitFor(".modal .pos-number-popup");
    await enterPinDigits(pin);
    await confirmPinPopup();
}

export async function login(name, pin = false) {
    await clickLoginButton();
    await selectCashierInPopup(name);
    if (pin) {
        await enterPin(pin);
    }
    await animationFrame();
}

// The CashierName navbar component is desktop-only, so small screens have to go back through
// the login screen to change cashier.
export async function switchCashier(name, pin = false) {
    if (isMobile()) {
        await clickLockButton();
        await login(name, pin);
        return;
    }
    await clickCashierName();
    await selectCashierInPopup(name);
    if (pin) {
        await enterPin(pin);
    }
    await animationFrame();
}

export async function openMenu() {
    await contains('.pos-rightheader .btn:has(i[data-icon="menu"])').click();
    await animationFrame();
    await waitFor(".pos-burger-menu-items");
}

const MENU_ITEM_SELECTOR =
    ".pos-burger-menu-items .dropdown-item, .pos-burger-menu-items .o-dropdown-item";

export function menuOptionNames() {
    return queryAll(MENU_ITEM_SELECTOR).map((el) => el.textContent.trim());
}

export function hasMenuOption(label) {
    return menuOptionNames().some((text) => text.includes(label));
}

export async function clickMenuOption(label) {
    const item = queryAll(MENU_ITEM_SELECTOR).find((el) => el.textContent.includes(label));
    await contains(item).click();
    await animationFrame();
}

export async function closeMenu() {
    await press("Escape");
    await animationFrame();
}

export async function createFloatingOrder() {
    await contains(".pos-leftheader .list-plus-btn").click();
    await animationFrame();
}

// Clicking an already selected line toggles the selection off, so only click when nothing is
// selected. Locking the register clears the selection, which small screens go through on every
// cashier switch.
export async function selectOrderlineIfNeeded(store, productName) {
    if (!store.getOrder()?.getSelectedOrderline()) {
        await clickOrderline(productName);
    }
}

export function ticketRowTexts() {
    return queryAll(".ticket-screen .order-row").map((el) => el.textContent);
}

export function ticketRowContains(index, text) {
    return (ticketRowTexts()[index - 1] || "").includes(text);
}
