import { negate } from "@point_of_sale/../tests/tours/utils/common";

export function confirm(confirmationText, button = ".btn-primary") {
    let trigger = `.modal .modal-footer ${button}`;
    if (confirmationText) {
        trigger += `:contains("${confirmationText}")`;
    }
    return {
        content: "confirm dialog",
        trigger,
        run: "click",
    };
}
export function cancel() {
    return {
        content: "cancel dialog",
        trigger: `.modal .modal-header button[aria-label="Close"]`,
        run: "click",
    };
}
export function discard() {
    return {
        content: "discard dialog",
        trigger: `.modal .modal-footer button:contains("Discard")`,
        run: "click",
    };
}
export function is({ title } = {}) {
    let trigger = ".modal .modal-content";
    if (title) {
        trigger += ` .modal-header:contains("${title}")`;
    }
    return {
        content: "dialog is open",
        trigger,
    };
}
export function isNot() {
    return {
        content: "no dialog is open",
        trigger: negate(".modal-open"),
    };
}

export function bodyIs(body) {
    return {
        content: "dialog is open",
        trigger: `.modal-body:contains(${body})`,
    };
}
