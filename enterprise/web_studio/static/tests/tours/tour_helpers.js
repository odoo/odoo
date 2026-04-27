/** @odoo-module */

export function assertEqual(actual, expected) {
    if (actual !== expected) {
        throw new Error(`Assert failed: expected: ${expected} ; got: ${actual}`);
    }
}

export async function nextTick() {
    await new Promise((resolve) => setTimeout(resolve));
    await new Promise((resolve) => requestAnimationFrame(resolve));
}

export function stepNotInStudio(trigger) {
    return [
        {
            trigger: "body:not(:has(.o_studio))",
        },
        {
            trigger: trigger || "body",
        },
    ];
}
