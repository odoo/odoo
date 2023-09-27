/** @odoo-module */

import * as SelectionPopup from "@point_of_sale/../tests/tours/helpers/SelectionPopupTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import * as NumberPopup from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";

export function clickLoginButton() {
    return [
        {
            content: "click login button",
            trigger: ".login-overlay .login-button.select-cashier",
        },
    ];
}
export function clickLockButton() {
    return [
        {
            content: "click lock button",
            trigger: ".lock-button",
        },
    ];
}
export function clickCashierName() {
    return [
        {
            content: "click cashier name",
            trigger: ".oe_status .username",
        },
    ];
}
export function loginScreenIsShown() {
    return [
        {
            content: "login screen is shown",
            trigger: ".login-overlay .screen-login .login-body",
            run: () => {},
        },
    ];
}
export function cashierNameIs(name) {
    return [
        {
            content: `logged cashier is '${name}'`,
            trigger: `.pos .oe_status .username:contains("${name}")`,
            run: () => {},
        },
    ];
}
export function login(name, pin) {
    const res = [...clickLoginButton(), ...SelectionPopup.has(name, { run: "click" })];
    if (!pin) {
        return res;
    }
    return res.concat([
        ...NumberPopup.pressNumpad(pin.split("").join(" ")),
        ...NumberPopup.isShown("••••"),
        Dialog.confirm(),
    ]);
}
