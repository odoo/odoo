import * as SelectionPopup from "@point_of_sale/../tests/tours/utils/selection_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";

export function clickLoginButton() {
    return [
        {
            content: "click login button",
            trigger: ".login-overlay .select-cashier",
            run: "click",
        },
    ];
}
export function clickCashierName() {
    return [
        {
            content: "click cashier name",
            trigger: ".cashier-name",
            run: "click",
        },
    ];
}
export function loginScreenIsShown() {
    return [
        {
            content: "login screen is shown",
            trigger: ".login-overlay .screen-login",
        },
    ];
}
export function cashierNameIs(name) {
    return [
        {
            isActive: ["desktop"],
            content: `logged cashier is '${name}'`,
            trigger: `.pos .oe_status .username:contains("${name}")`,
        },
        {
            isActive: ["mobile"],
            content: `logged cashier is '${name}'`,
            trigger: `.pos .oe_status img[alt="${name}"]`,
        },
    ];
}
export function login(name, pin) {
    const res = [...clickLoginButton(), ...SelectionPopup.has(name, { run: "click" })];
    if (!pin) {
        return res;
    }
    return res.concat([
        ...NumberPopup.enterValue(pin),
        ...NumberPopup.isShown("••••"),
        Dialog.confirm(),
    ]);
}
export function clickLockButton() {
    return {
        content: "Click on the menu button",
        trigger: ".pos-rightheader i.fa-unlock",
        run: "click",
    };
}

export function refreshPage() {
    return [
        {
            trigger: ".pos",
            run: () => {
                window.location.reload();
            },
            expectUnloadPage: true,
        },
    ];
}
