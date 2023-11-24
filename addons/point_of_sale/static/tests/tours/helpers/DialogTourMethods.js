/** @odoo-module **/

import { negate } from "@point_of_sale/../tests/tours/helpers/utils";

export function confirm(confirmationText) {
    let trigger = ".modal-footer .btn-primary";
    if (confirmationText) {
        trigger += `:contains("${confirmationText}")`;
    }
    return {
        content: "confirm dialog",
        in_modal: true,
        trigger,
    };
}
export function cancel() {
    return {
        content: "cancel dialog",
        trigger: `.modal-header button[aria-label="Close"]`,
        in_modal: true,
    };
}
export function is() {
    return {
        content: "dialog is open",
        trigger: ".modal-body",
        in_modal: true,
        isCheck: true,
    };
}
export function isNot() {
    return {
        content: "no dialog is open",
        trigger: negate(".modal-open"),
        isCheck: true,
    };
}
