import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function clickNumpad(digit) {
    await contains(`.numpad button:contains("${digit}")`).click();
    await animationFrame();
}
