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

export function stepNextTick() {
    // FIXME: this probably should be handled by the tour-as-macro infrastructure
    // The case is to have a dom node with a constant selector. It will trigger the next step
    // even though the element will be changed after, resulting in non-deterministic bugs.
    // This is especially the case in the case of inputs, where we'd want to assert their value changed
    return {
        trigger: "body",
        run() {
            return nextTick();
        },
    };
}

export function stepNotInStudio(trigger) {
    return {
        extra_trigger: "body:not(:has(.o_studio))",
        trigger: trigger || "body",
        isCheck: true,
    };
}
