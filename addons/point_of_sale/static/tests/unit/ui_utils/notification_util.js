import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { normalizeText } from "./common";

export function notifications() {
    return [...document.querySelectorAll(".o_notification")].map((el) => ({
        type: [...el.querySelector(".o_notification_bar").classList]
            .find((cls) => cls.startsWith("bg-"))
            .slice("bg-".length),
        message: normalizeText(el.querySelector(".o_notification_content").textContent),
    }));
}

export async function closeNotifications() {
    for (const button of [...document.querySelectorAll(".o_notification_close")]) {
        await contains(button).click();
    }
    await animationFrame();
}
