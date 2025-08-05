import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { negate } from "@point_of_sale/../tests/generic_helpers/utils";
import { waitFor } from "@odoo/hoot-dom";
const { DateTime } = luxon;

export function confirmPopup() {
    return [Dialog.confirm()];
}
export function clickMenuButton() {
    return {
        content: "Click on the menu button",
        trigger: ".pos-rightheader button:has(.fa-bars)",
        run: "click",
    };
}
export function clickMenuOption(name, options) {
    return [clickMenuButton(), clickMenuDropdownOption(name, options)];
}
export function clickMenuDropdownOption(name, { expectUnloadPage = false } = {}) {
    return {
        content: `click on something in the burger menu`,
        trigger: `span.dropdown-item:contains(${name})`,
        run: "click",
        expectUnloadPage,
    };
}
export function isCashMoveButtonHidden() {
    return [
        {
            trigger: ".pos-topheader:not(:contains(Cash In/Out))",
        },
    ];
}
export function doCashMove(amount, reason, cashSign = "out", cashType = "") {
    return [
        ...clickMenuOption("Cash In/Out"),
        fillTextArea(".cash-reason", reason),
        {
            trigger: `input[type="radio"][value="${cashSign}"]`,
            run: "click",
        },
        {
            trigger: ".modal .input-amount input",
            run: "edit " + amount,
        },
        {
            trigger: ".form-select",
            run: "select " + cashType,
        },
        Dialog.confirm(),
    ];
}
export function endTour() {
    return {
        content: "Last tour step that avoids error mentioned in commit 443c209",
        trigger: "body",
    };
}
export function isSyncStatusConnected() {
    return {
        trigger: negate(".oe_status", ".pos-rightheader .status-buttons"),
    };
}
export function clickPlanButton() {
    return {
        content: "go back to the floor screen",
        trigger: ".pos-leftheader .table-button",
        run: "click",
    };
}
export function startPoS() {
    return [
        {
            content: "Start PoS",
            trigger: ".screen-login .btn.open-register-btn",
            run: "click",
        },
    ];
}
export function clickBtn(name, { expectUnloadPage = false } = {}) {
    return {
        content: `Click on ${name}`,
        trigger: `body button:contains(${name})`,
        run: "click",
        expectUnloadPage,
    };
}
export function fillTextArea(target, value) {
    return {
        content: `Fill text area with ${value}`,
        trigger: `textarea${target}`,
        run: `edit ${value}`,
    };
}
export function createFloatingOrder() {
    return { trigger: ".pos-leftheader .list-plus-btn", run: "click" };
}

function _hasFloatingOrder(name, yes) {
    const negateIfNecessary = (trigger) => (yes ? trigger : negate(trigger));
    return [
        {
            isActive: ["desktop"],
            trigger: negateIfNecessary(
                `.pos-topheader .floating-order-container:contains('${name}')`
            ),
        },
        {
            isActive: ["mobile"],
            trigger: ".pos-leftheader button.fa-caret-down",
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: negateIfNecessary(
                `.modal-header:contains(Choose an order) ~ .modal-body .floating-order-container:contains('${name}')`
            ),
        },
        {
            isActive: ["mobile"],
            trigger: ".oi-arrow-left",
            run: "click",
        },
    ];
}

export function hasFloatingOrder(name) {
    return _hasFloatingOrder(name, true);
}

export function noFloatingOrder(name) {
    return _hasFloatingOrder(name, false);
}
export function clickOrders() {
    return { trigger: ".pos-leftheader .orders-button", run: "click" };
}
export function clickPresetTimingSlot() {
    return { trigger: ".pos-leftheader .preset-time-btn", run: "click" };
}
export function presetTimingSlotIs(hour) {
    return { trigger: `.pos-leftheader .preset-time-btn:contains('${hour}')` };
}
export function selectPresetTimingSlotHour(hour) {
    return { trigger: `.modal button:contains('${hour}')`, run: "click" };
}
export function clickRegister() {
    return { trigger: ".pos-leftheader .register-label", run: "click" };
}
export function waitRequest() {
    return [
        {
            trigger: "body",
            content: "Wait loading is finished if it is shown",
            timeout: 15000,
            async run() {
                let isLoading = false;
                try {
                    isLoading = await waitFor("body:has(.fa-circle-o-notch)", { timeout: 2000 });
                } catch {
                    /* fa-circle-o-notch will certainly never appears :'( */
                }
                if (isLoading) {
                    await waitFor("body:not(:has(.fa-circle-o-notch))", { timeout: 10000 });
                }
            },
        },
    ];
}

export function isSynced() {
    return {
        content: "Check if the request is proceeded",
        trigger: negate(".fa-spin", ".status-buttons"),
    };
}

export function freezeDateTime(millis) {
    return [
        {
            trigger: "body",
            run: () => {
                DateTime.now = () => DateTime.fromMillis(millis);
            },
        },
    ];
}

export function selectPresetDateButton(formattedDate) {
    return {
        trigger: `.modal-body button:contains("${formattedDate}")`,
        run: "click",
    };
}
