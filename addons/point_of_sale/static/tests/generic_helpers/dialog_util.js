import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

export function confirm(confirmationText, button = ".btn-primary") {
    let trigger = `.modal:not(.o_inactive_modal) .modal-footer ${button}`;
    if (confirmationText) {
        trigger += `:contains("${confirmationText}")`;
    }
    return {
        content: "confirm dialog",
        trigger,
        run: "click",
    };
}
export function cancel({ title } = {}) {
    return {
        content: "cancel dialog",
        trigger: `.modal .modal-header${
            title ? `:contains(${title})` : ""
        } button[aria-label="Close"]`,
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
export function isNot(...args) {
    const { trigger } = is(...args);
    return {
        content: "no dialog is open",
        trigger: negate(trigger),
    };
}

export function bodyIs(body) {
    return {
        content: "dialog is open",
        trigger: `.modal-body:contains(${body})`,
    };
}

export function footerBtnIsDisabled(buttonText) {
    return {
        content: `footer btn ${buttonText} should be disabled`,
        trigger: `.modal .modal-footer button:contains(${buttonText})[disabled]`,
    };
}
