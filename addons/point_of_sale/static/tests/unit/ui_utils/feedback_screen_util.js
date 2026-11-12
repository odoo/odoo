import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function clickNextOrder() {
    await contains(".feedback-screen .validation:not(:disabled)").click();
    await animationFrame();
}
