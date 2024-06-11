/** @odoo-module */

export function clickConfirm() {
    return [
        {
            content: "click confirm button",
            trigger: ".popup-error .footer .cancel",
        },
    ];
}

export function isShown() {
    return [
        {
            content: "error popup is shown",
            trigger: ".modal-dialog .popup-error",
            run: () => {},
        },
    ];
}
