import { animationFrame, advanceTime } from "@odoo/hoot-dom";
import { getService } from "@web/../tests/web_test_helpers";

export function normalizeText(text) {
    return text.replaceAll("\u00a0", " ").trim();
}

export function isMobile() {
    return getService("ui").isSmall;
}

export async function ensurePane(targetPane) {
    if (!isMobile()) {
        return;
    }
    const pos = getService("pos");
    if (pos.mobile_pane !== targetPane) {
        pos.switchPane();
        await animationFrame();
    }
}

export async function ensureTicketPane(targetPane) {
    if (!isMobile()) {
        return;
    }
    const pos = getService("pos");
    if (pos.ticket_screen_mobile_pane !== targetPane) {
        pos.switchPaneTicketScreen();
        await animationFrame();
    }
}

export function queryEl(selector, text) {
    const els = document.querySelectorAll(selector);
    if (!text) {
        return els[0] || null;
    }
    for (const el of els) {
        if (el.textContent.includes(text)) {
            return el;
        }
    }
    return null;
}

export async function longPress(target, fallbackSelector = "article.product") {
    let el;
    if (typeof target === "string") {
        el = document.querySelector(target);
        if (!el) {
            const elements = document.querySelectorAll(fallbackSelector);
            for (const p of elements) {
                if (p.textContent.includes(target)) {
                    el = p;
                    break;
                }
            }
        }
    } else {
        el = target;
    }
    el.dispatchEvent(
        new PointerEvent("pointerdown", { bubbles: true, pointerType: "mouse", button: 0 })
    );
    await advanceTime(600);
    el.dispatchEvent(
        new PointerEvent("pointerup", { bubbles: true, pointerType: "mouse", button: 0 })
    );
    await animationFrame();
}
