/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import { SelectionPopup } from "@point_of_sale/../tests/tours/helpers/SelectionPopupTourMethods";
import { NumberPopup } from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";

class Do {
    clickLoginButton() {
        return [
            {
                content: "click login button",
                trigger: ".login-overlay .login-button.select-cashier",
            },
        ];
    }
    clickLockButton() {
        return [
            {
                content: "click lock button",
                trigger: ".header-button .lock-button",
            },
        ];
    }
    clickCashierName() {
        return [
            {
                content: "click cashier name",
                trigger: ".oe_status .username",
            },
        ];
    }
}
class Check {
    loginScreenIsShown() {
        return [
            {
                content: "login screen is shown",
                trigger: ".login-overlay .screen-login .login-body",
                run: () => {},
            },
        ];
    }
    cashierNameIs(name) {
        return [
            {
                content: `logged cashier is '${name}'`,
                trigger: `.pos .oe_status .username:contains("${name}")`,
                run: () => {},
            },
        ];
    }
}
class Execute {
    login(name, pin) {
        const res = this._do.clickLoginButton();
        res.push(...SelectionPopup._do.clickItem(name));
        if (pin) {
            res.push(...NumberPopup._do.pressNumpad(pin.split("").join(" ")));
            res.push(...NumberPopup._do.clickConfirm());
        }
        return res;
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("PosHr", Do, Check, Execute));
