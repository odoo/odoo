/** @odoo-module */

import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";

/**
 * Note: Maximum of 2 characters because NumberBuffer only allows 2 consecutive
 * fast inputs. Fast inputs is the case in tours.
 *
 * @param {String} keys space-separated input keys
 */
export function pressNumpad(keys) {
    return keys.split(" ").map((key) => Numpad.click(key, { mobile: false }));
}
export function enterValue(keys) {
    const numpadKeys = keys.split("").join(" ");
    return [...this.pressNumpad(numpadKeys), ...this.fillPopupValue(keys)];
}
export function fillPopupValue(keys) {
    return [
        {
            content: `'${keys}' inputed in the number popup`,
            trigger: ".popup .value",
            run: `text ${keys}`,
            mobile: true,
        },
    ];
}
export function clickConfirm() {
    return [
        {
            content: "click confirm button",
            trigger: ".popup-number .footer .confirm",
            mobile: false,
        },
        {
            content: "click confirm button",
            trigger: ".popup .footer .confirm",
            mobile: true,
        },
    ];
}

export function isShown() {
    return [
        {
            content: "number popup is shown",
            trigger: ".modal-dialog .popup .value",
            run: () => {},
        },
    ];
}
export function inputShownIs(val) {
    return [
        {
            content: "number input element check",
            trigger: ".modal-dialog .popup-number",
            run: () => {},
            mobile: false,
        },
        {
            content: `input shown is '${val}'`,
            trigger: `.modal-dialog .popup .value:contains("${val}")`,
            run: () => {},
            mobile: false,
        },
    ];
}
