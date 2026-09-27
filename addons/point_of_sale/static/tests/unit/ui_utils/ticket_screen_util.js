import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { ensureTicketPane, isMobile } from "./common";

export async function selectTicketFilter(filterName) {
    await contains(".ticket-screen .filter").click();
    await animationFrame();
    await contains(`.dropdown-item:contains("${filterName}")`).click();
    await animationFrame();
}

export async function selectTicketOrder(reference) {
    await ensureTicketPane("left");
    await contains(`.ticket-screen .order-row:contains("${reference}")`).click();
    await animationFrame();
}

export async function loadSelectedOrder() {
    if (isMobile()) {
        await ensureTicketPane("left");
        await contains(".ticket-screen .load-order-button").click();
    } else {
        await contains(".ticket-screen .pads .btn-primary").click();
    }
    await animationFrame();
}

export async function clickTicketReviewButton() {
    await ensureTicketPane("left");
    await contains(".ticket-screen .review-button").click();
    await animationFrame();
}

export async function clickTicketAction(buttonText) {
    await ensureTicketPane("right");
    await contains(`.ticket-screen .pads button:contains("${buttonText}")`).click();
    await animationFrame();
}

export async function clickTicketNumpad(key) {
    if (isMobile()) {
        await ensureTicketPane("right");
    }
    const label = key === "backspace" ? "⌫" : key;
    await contains(`.ticket-screen .numpad button:contains("${label}")`).click();
    await animationFrame();
}

export async function clickDeleteOrderOnTicket(orderRef) {
    await ensureTicketPane("left");
    if (orderRef) {
        await selectTicketOrder(orderRef);
    }
    if (isMobile()) {
        const row = document.querySelector(`.ticket-screen .order-row.highlight [name="delete"]`);
        if (row) {
            await contains(row).click();
        } else {
            await contains(`.ticket-screen .order-row.highlight [data-icon='delete']`).click();
        }
    } else {
        if (orderRef) {
            await contains(
                `.ticket-screen .order-row:contains("${orderRef}") .delete-column button`
            ).click();
        } else {
            await contains(".ticket-screen .order-row .delete-column button").click();
        }
    }
    await animationFrame();
}
