/** @odoo-module */

export function inputText(val) {
    return {
        content: `input text '${val}'`,
        trigger: `textarea`,
        in_modal: true,
        run: `edit ${val}`,
    };
}
