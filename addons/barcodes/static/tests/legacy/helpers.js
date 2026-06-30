import { triggerEvent } from "@web/../tests/helpers/utils";

export function simulateBarCode(chars, target = document.body, selector = undefined) {
    for (let char of chars) {
        triggerEvent(target, selector, "keydown", {
            key: char,
        });
    }
}
