/* @odoo-module */

import { triggerEvent } from "@web/../tests/helpers/utils";

export function simulateBarCode(chars, target = document.body, selector = undefined) {
    for (let char of chars) {
        let keycode;
        if (char === "Enter") {
            keycode = $.ui.keyCode.ENTER;
        } else if (char === "Tab") {
            keycode = $.ui.keyCode.TAB;
        } else {
            keycode = char.charCodeAt(0);
        }
        triggerEvent(target, selector, "keydown", {
            key: char,
            keyCode: keycode,
        });
    }
}
