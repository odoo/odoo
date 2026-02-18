import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

function buildTrigger({ title, body } = {}) {
    let selector = `.modal:not(.o_inactive_modal)`;

    if (title) {
        selector += `:has(.modal-title:contains("${title}"))`;
    }

    if (body) {
        selector += `:has(.modal-body:contains("${body}"))`;
    }
    return selector;
}

export function confirm(confirmationText, button = ".btn-primary") {
    let trigger = `${buildTrigger()} .modal-footer ${button}`;
    if (confirmationText) {
        trigger += `:contains("${confirmationText}")`;
    }
    return {
        content: "confirm dialog",
        trigger,
        run: "click",
    };
}

export function proceed({ title, body, button, buttonClass = ".btn-primary" } = {}) {
    let trigger = `${buildTrigger({ title, body })} .modal-footer ${buttonClass}`;
    if (button) {
        trigger += `:contains("${button}")`;
    }
    return {
        content: "proceed click action on dialog",
        trigger,
        run: "click",
    };
}

export function cancel({ title, body } = {}) {
    return {
        content: "cancel dialog",
        trigger: `${buildTrigger({ title, body })} .modal-header button[aria-label="Close"]`,
        run: "click",
    };
}
export function discard({ title, body } = {}) {
    return {
        content: "discard dialog",
        trigger: `${buildTrigger({ title, body })} .modal-footer button:contains("Discard")`,
        run: "click",
    };
}
export function is({ title, body } = {}) {
    const trigger = buildTrigger({ title, body });
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
