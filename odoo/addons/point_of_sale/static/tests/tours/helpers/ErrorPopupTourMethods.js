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

export function messageBodyContains(text) {
    return [
        {
            content: `check '${text}' is in the body of the popup`,
            trigger: `.modal-dialog .popup-error .modal-body:contains(${text})`,
        },
    ];
}
