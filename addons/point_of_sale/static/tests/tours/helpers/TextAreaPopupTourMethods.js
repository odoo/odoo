/** @odoo-module */

export function inputText(val) {
    return [
        {
            content: `input text '${val}'`,
            trigger: `.modal-dialog .popup-textarea textarea`,
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
            trigger: ".modal-dialog .popup-textarea",
            run: () => {},
        },
    ];
}
