/* global posmodel */
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { negate } from "@point_of_sale/../tests/generic_helpers/utils";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
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
    return [
        waitForMenuButtons(),
        clickMenuButton(),
        waitForMenuOptionsToOpen(),
        clickMenuDropdownOption(name, options),
    ];
}
export function waitForMenuButtons() {
    return {
        content: "Wait for the menu buttons to be available",
        trigger: ".pos-rightheader button:has(.fa-bars)",
    };
}
export function waitForMenuOptionsToOpen() {
    return {
        content: `Wait for the menu options to be available`,
        trigger: `span.dropdown-item`,
    };
}
export function clickMenuDropdownOption(name, { expectUnloadPage = false } = {}) {
    return {
        content: `click on something in the burger menu`,
        trigger: `span.dropdown-item:contains(${name})`,
        run: "click",
        expectUnloadPage,
    };
}
export function existMenuOption(name) {
    return [
        clickMenuButton(),
        {
            content: `check that ${name} exists in the burger menu`,
            trigger: `span.dropdown-item:contains(${name})`,
        },
        clickMenuButton(),
    ];
}
export function notExistMenuOption(name) {
    return [
        clickMenuButton(),
        {
            content: `check that ${name} doesn't exist in the burger menu`,
            trigger: negate(`span.dropdown-item:contains(${name})`),
        },
    ];
}
export function isCashMoveButtonHidden() {
    return [
        {
            trigger: ".pos-topheader:not(:contains(Cash In/Out))",
        },
    ];
}
export function doCashMove(amount, reason) {
    const numpadWrite = (val) => val.split("").flatMap((key) => Numpad.click(key));
    return [
        ...clickMenuOption("Cash In/Out"),
        fillTextArea(".cash-reason", reason),
        {
            isActive: ["desktop"],
            content: "Enter the amount to cash in/out",
            trigger: ".modal input.o_input",
            run: "edit " + amount,
        },
        {
            isActive: ["mobile"],
            content: "Enter the amount to cash in/out",
            trigger: ".modal input.o_input",
            run: "click",
        },
        ...numpadWrite(amount).map((step) => ({
            isActive: ["mobile"],
            ...step,
        })),
        {
            isActive: ["mobile"],
            trigger: ".o-overlay-item:nth-child(2) .modal-footer button:contains('Ok')",
            run: "click",
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
    return [
        {
            content: "go back to the floor screen",
            trigger: ".pos-leftheader .table-button",
            run: "click",
        },
        ...waitRequest(),
    ];
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
            async run({ waitFor }) {
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

export function storedOrderCount(expectedCount) {
    return {
        content: `Stored order count should be ${expectedCount}`,
        trigger: "body",
        run: () => {
            const actualCount = posmodel.data.models["pos.order"].length;
            if (actualCount !== expectedCount) {
                throw new Error(
                    `Expected stored order count to be ${expectedCount}, but got ${actualCount}`
                );
            }
        },
    };
}

export function isSynced() {
    return {
        content: "Check if the request is proceeded",
        trigger: negate(".fa-spin", ".status-buttons"),
    };
}

export function clickOnScanButton() {
    return {
        content: "Click the Scan button located in the top header.",
        trigger: ".pos-topheader .status-buttons .fa-barcode",
        run: "click",
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
