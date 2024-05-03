import { negate } from "@point_of_sale/../tests/tours/utils/common";

export function confirm(confirmationText, button = ".btn-primary") {
    let trigger = `.modal-footer ${button}`;
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
export function is({ title } = {}) {
    let trigger = ".modal-content";
    if (title) {
        trigger += ` .modal-header:contains("${title}")`;
    }
    return {
        content: "dialog is open",
        trigger,
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
