import { expect } from "@odoo/hoot";
import { advanceTime, animationFrame, waitFor, waitUntil, press } from "@odoo/hoot-dom";
import { contains, getService } from "@web/../tests/web_test_helpers";
import { expectFormattedPrice } from "@point_of_sale/../tests/unit/utils";
import {
    addOrderlineFromProductScreen as posAddOrderlineFromProductScreen,
    clickControlButton,
    clickNextOrder,
    clickPartnerButton,
    clickPayButton,
    clickPaymentMethod,
    clickValidatePayment,
    ensurePane,
    getOrderTotal,
    hasOrderline,
    sendBufferKeys,
} from "@point_of_sale/../tests/unit/ui_utils";
import { PosNumberBufferPlugin } from "@point_of_sale/app/plugins/pos_number_buffer_plugin";

const ORDER_TOTAL_TIMEOUT = 3000;
const SETTLE_STEP = 50;

async function waitForLoyalty(condition, { timeout = ORDER_TOTAL_TIMEOUT } = {}) {
    for (let waited = 0; waited < timeout; waited += SETTLE_STEP) {
        if (condition()) {
            return true;
        }
        await advanceTime(SETTLE_STEP);
    }
    return Boolean(condition());
}

export async function addOrderlineFromProductScreen(productName, options) {
    await posAddOrderlineFromProductScreen(productName, options);
    const numberBuffer = getService(PosNumberBufferPlugin);
    await waitForLoyalty(() => !numberBuffer.hasPendingInput());
    await animationFrame();
}

export async function openControlButtons() {
    if (!document.querySelector(".control-buttons-modal")) {
        await ensurePane("left");
        await contains(".product-screen .more-btn, .product-screen .mobile-more-button").click();
        await animationFrame();
        await waitFor(".control-buttons-modal");
    }
}

export async function getControlButton(label) {
    await waitFor(`.control-button:contains("${label}")`);
    return [...document.querySelectorAll(".control-button")].find(
        (el) => el.textContent.trim() === label
    );
}

export async function clickSelectionPopupItem(label) {
    await waitFor(".selection-item");
    await contains(`.selection-item:contains("${label}")`).click();
    await animationFrame();
}

export async function enterCode(code) {
    await clickControlButton("Enter Code");
    await waitFor(".modal textarea");
    await contains(".modal textarea").edit(code);
    await contains('.modal .btn-primary:contains("Apply")').click();
    await animationFrame();
}

export async function claimReward(label) {
    await clickControlButton("Reward");
    await clickSelectionPopupItem(label);
}

async function closeDialogWithEscape(selector) {
    await press("Escape");
    await animationFrame();
    await waitUntil(() => !document.querySelector(selector));
    await sendBufferKeys();
}

export async function saveOrder() {
    await ensurePane("left");
    await contains(".pads [data-icon='upload']").click();
    await animationFrame();
}

export function expectPointsAwarded(points) {
    expect(document.querySelector(".loyalty-points-won")?.textContent).toInclude(points, {
        message: `expected ${points} loyalty points to be awarded`,
    });
}

export async function expectPartnerPoints(name, points) {
    await ensurePane("left");
    await clickPartnerButton();
    await waitFor(`.partner-list .partner-line:contains("${name}")`);
    const line = [...document.querySelectorAll(".partner-list .partner-line")].find((el) =>
        el.textContent.includes(name)
    );
    expect(line?.querySelector(".partner-line-balance")?.textContent).toInclude(points, {
        message: `expected "${name}" to show ${points}`,
    });
    await closeDialogWithEscape(".partner-list");
}

export function expectPointsTotal(points) {
    expect(document.querySelector(".loyalty-points-total")?.textContent).toInclude(points, {
        message: `expected a loyalty points total of ${points}`,
    });
}

export async function selectRewardOrderline(name) {
    await ensurePane("left");
    await contains(`.orderline.fst-italic .product-name:contains("${name}")`).click();
    await animationFrame();
}

export async function waitForOrderTotal(store, total, timeoutMessage) {
    const reached = await waitForLoyalty(
        () => Math.abs(store.getOrder().priceIncl - total) < 0.00001
    );
    if (!reached) {
        throw new Error(`${timeoutMessage} (expected ${total}, got ${store.getOrder().priceIncl})`);
    }
    await animationFrame();
}

export function expectOrderTotal(amount) {
    expectFormattedPrice(getOrderTotal(), `$ ${amount}`);
}

export function expectRewardLine(description, amount, quantity) {
    expect(
        hasOrderline({
            withClass: ".fst-italic",
            productName: description,
            price: amount,
            quantity,
        })
    ).toBe(true, {
        message: `expected a reward line "${description}" at ${amount}${
            quantity === undefined ? "" : ` x${quantity}`
        }`,
    });
}

export function expectNoRewardLine(description) {
    const line = [...document.querySelectorAll(".order-container .orderline.fst-italic")].find(
        (el) => el.querySelector(".product-name")?.textContent.includes(description)
    );
    expect(line).toBe(undefined, {
        message: `expected no reward line for "${description}"`,
    });
}

export async function expectRewardButtonHighlighted(highlighted, closeModal = true) {
    const expectedClass = highlighted ? "active" : "disabled";
    await openControlButtons();
    const button = await getControlButton("Reward");
    expect(button.classList.contains(expectedClass)).toBe(true, {
        message: `expected the Reward button to be ${highlighted ? "highlighted" : "disabled"}`,
    });
    if (closeModal) {
        await closeDialogWithEscape(".control-buttons-modal");
    }
}

export async function finalizeOrder(paymentMethod, amount) {
    await clickPayButton();
    await clickPaymentMethod(paymentMethod);
    await sendBufferKeys(...amount.toString().split(""));
    await clickValidatePayment();
    await waitFor(".feedback-screen");
    await clickNextOrder();
    await waitFor(".product-screen");
    getService("pos").getOrder()?.setPricelist(false);
    await animationFrame();
}
