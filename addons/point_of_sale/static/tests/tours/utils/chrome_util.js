import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { negate } from "@point_of_sale/../tests/tours/utils/common";

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
        trigger: ".pos-leftheader .back-button:not(:has(.btn-primary))",
        run: "click",
    };
}
export function clickFloatingOrder(orderName) {
    return [
        {
            isActive: ["mobile"],
            trigger: ".pos-leftheader button.fa-caret-down",
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: "click on the floating order " + orderName,
            trigger: `.modal-dialog button:contains("${orderName}")`,
            run: "click",
        },
        {
            isActive: ["desktop"],
            content: "click on the floating order " + orderName,
            trigger: `.pos-leftheader button:contains("${orderName}")`,
            run: "click",
        },
    ];
}
export function newFloatingOrder() {
    return {
        content: "click on the new floating order button",
        trigger: ".pos-leftheader button i.fa-plus-circle",
        run: "click",
    };
}

export function floatingOrderDoesNotExist(orderName) {
    return [
        {
            isActive: ["mobile"],
            trigger: ".pos-leftheader button.fa-caret-down",
            run: "click",
        },
        {
            isActive: ["mobile"],
            content: "click on the floating order " + orderName,
            trigger: negate(`.modal-body button:contains("${orderName}")`),
        },
        {
            isActive: ["desktop"],
            content: "click on the floating order " + orderName,
            trigger: negate(`button:contains("${orderName}")`, ".pos-leftheader"),
        },
        {
            ...Dialog.cancel(),
            isActive: ["mobile"],
        },
    ];
}
