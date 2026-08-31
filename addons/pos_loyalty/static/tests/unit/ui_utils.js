import { expect } from "@odoo/hoot";
import { animationFrame, waitFor, waitUntil, press } from "@odoo/hoot-dom";
import { contains, getService } from "@web/../tests/web_test_helpers";
import { expectFormattedPrice } from "@point_of_sale/../tests/unit/utils";
import {
    clickControlButton,
    clickNextOrder,
    clickPartnerButton,
    isMobile,
    clickPayButton,
    clickPaymentMethod,
    clickValidatePayment,
    ensurePane,
    hasOrderline,
    sendBufferKeys,
} from "@point_of_sale/../tests/unit/ui_utils";

const ORDER_TOTAL_TIMEOUT = 3000;

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

export async function clickProductNamed(name) {
    await waitFor("article.product .product-name");
    const nameEl = [...document.querySelectorAll("article.product .product-name")].find(
        (el) => el.textContent.trim() === name
    );
    await contains(nameEl).click();
    await animationFrame();
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

export async function clickPriceList(name) {
    await clickControlButton("Pricelist");
    await waitFor(".selection-item");
    await contains(`.selection-item:contains("${name}")`).click();
    await animationFrame();
}

export async function cancelActiveDialog() {
    await contains('.modal:not(.o_inactive_modal) .modal-header [aria-label="Close"]').click();
    await animationFrame();
}

/**
 * Close the dialog matching `selector` with Escape. The Escape keyup also lands in the
 * number buffer, which drops its whole content as soon as it holds one non-numeric key,
 * so flush it right away — otherwise the next key the test sends is swallowed with it.
 */
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

export async function selectFloatingOrder(index) {
    if (isMobile()) {
        await contains("[data-icon='arrow_drop_down']").click();
        await animationFrame();
        const mobileButtons = document.querySelectorAll(".modal-dialog .list-container-items .btn");
        await contains(mobileButtons[index]).click();
    } else {
        const buttons = document.querySelectorAll(
            ".list-container-items .floating-order-container .btn"
        );
        await contains(buttons[index]).click();
    }
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
    try {
        await waitUntil(() => Math.abs(store.getOrder().priceIncl - total) < 0.00001, {
            timeout: ORDER_TOTAL_TIMEOUT,
        });
    } catch {
        throw new Error(`${timeoutMessage} (expected ${total}, got ${store.getOrder().priceIncl})`);
    }
}

export function expectOrderTotal(amount) {
    expectFormattedPrice(
        document.querySelector(".order-summary .total").textContent,
        `$ ${amount}`
    );
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
    await openControlButtons();
    const button = await getControlButton("Reward");
    expect(button.classList.contains(highlighted ? "highlight" : "disabled")).toBe(true, {
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
