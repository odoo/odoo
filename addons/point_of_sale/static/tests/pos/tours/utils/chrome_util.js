import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

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
export function clickMenuOption(name) {
    return [clickMenuButton(), clickMenuDropdownOption(name)];
}
export function clickMenuDropdownOption(name) {
    return {
        content: `click on something in the burger menu`,
        trigger: `span.dropdown-item:contains(${name})`,
        run: "click",
    };
}
export function isCashMoveButtonHidden() {
    return [
        {
            trigger: ".pos-topheader:not(:contains(Cash In/Out))",
        },
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
export function clickBtn(name) {
    return {
        content: `Click on ${name}`,
        trigger: `body button:contains(${name})`,
        run: "click",
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
export function clickRegister() {
    return { trigger: ".pos-leftheader .register-label", run: "click" };
}
