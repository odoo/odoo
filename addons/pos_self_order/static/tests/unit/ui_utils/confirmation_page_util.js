import { waitFor, queryFirst, animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function checkConfirmationPage() {
    await waitFor(".confirmation-page");
}

export async function checkConfirmationString(timingPreset = false) {
    if (timingPreset) {
        await waitFor('.confirmation-block h1:contains("Order for")');
    } else {
        await waitFor('.confirmation-block h1:contains("We\'re preparing your order!")');
    }
}

export async function checkOrderNumberShown() {
    await waitFor(".tracking-number");
}

export async function checkOrderNumberIs(prefix, num) {
    const span = queryFirst("span.tracking-number");
    const text = span?.textContent || "";
    if (!text.startsWith(prefix) || !text.endsWith(num)) {
        throw new Error(
            `Order number '${text}' does not start with '${prefix}' and end with '${num}'`
        );
    }
}

export async function clickConfirmationPage() {
    await waitFor(".o_pos_status_base button:enabled");
    await contains(".tracking-number").click();
    await animationFrame();
}
