import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

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
        },
    ];
}

export function editCreateProductFlow(access = true) {
    return [
        ProductScreen.clickInfoProduct("Desk Pad", "1"),
        {
            trigger: access
                ? `.modal .modal-footer .btn-secondary:contains("Edit")`
                : negate(`.modal .modal-footer .btn-secondary:contains("Edit")`),
        },
        Dialog.cancel(),
        Chrome.clickMenuButton(),
        {
            trigger: access
                ? `span.dropdown-item:contains("Create Product")`
                : negate(`span.dropdown-item:contains("Create Product")`),
        },
    ];
}

export function testUserAccess(employeeName, hasAccess) {
    return [
        clickCashierName(),
        SelectionPopup.has(employeeName, { run: "click" }),
        ...editCreateProductFlow(hasAccess),
    ];
}
