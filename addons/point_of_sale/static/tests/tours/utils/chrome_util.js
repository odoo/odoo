import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";

export function confirmPopup() {
    return [Dialog.confirm()];
}
export function clickMenuButton() {
    return {
        content: "Click on the menu button",
        trigger: ".pos-rightheader button.fa-bars",
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
export function newOrder() {
    return {
        content: "create new order",
        trigger: ".pos-topheader button i.fa-plus-circle",
        run: "click",
    };
}
export function endTour() {
    return {
        content: "Last tour step that avoids error mentioned in commit 443c209",
        trigger: "body",
    };
}
export function createFloatingOrder() {
    return { trigger: ".pos-topheader .list-plus-btn", run: "click" };
}

export function isSynced() {
    return {
        content: "Check if the request is proceeded",
        trigger: ".oe_status .fa-wifi",
    };
}
