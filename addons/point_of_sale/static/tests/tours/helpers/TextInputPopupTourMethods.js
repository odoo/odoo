/** @odoo-module */

export function inputText(val) {
    return [
        {
            content: `input text '${val}'`,
            trigger: `.modal-dialog .popup-textinput input`,
            run: `text ${val}`,
        },
    ];
}
export function clickConfirm() {
    return [
        {
            content: "confirm text input popup",
            trigger: ".modal-dialog .confirm",
        },
    ];
}

export function isShown() {
    return [
        {
            content: "text input popup is shown",
            trigger: ".modal-dialog .popup-textinput",
            run: () => {},
        },
    ];
}

export function clickCancel() {
    return [
        {
            content: "discard text input popup",
            trigger: ".modal-dialog .cancel",
        },
    ];
}

export function checkConfirmDisabled() {
    return [
        {
            content: "confirm button disabled",
            trigger: ".modal-dialog .confirm.disabled",
            isCheck: true,
        },
    ];
}
