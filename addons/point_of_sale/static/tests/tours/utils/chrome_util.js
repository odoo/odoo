import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";

export function confirmPopup() {
    return [Dialog.confirm()];
}
export function clickMenuButton() {
    return {
        content: "Click on the menu button",
        trigger: ".pos-rightheader button.fa-bars",
    };
}
export function clickMenuOption(name) {
    return [clickMenuButton(), clickMenuDropdownOption(name)];
}
export function clickMenuDropdownOption(name) {
    return {
        content: `click on something in the burger menu`,
        trigger: `span.dropdown-item:contains(${name})`,
    };
}
export function isCashMoveButtonHidden() {
    return [
        {
            extraTrigger: ".pos-topheader",
            trigger: ".pos-topheader:not(:contains(Cash In/Out))",
            run: () => {},
        },
    ];
}
export function endTour() {
    return {
        content: "Last tour step that avoids error mentioned in commit 443c209",
        trigger: "body",
        isCheck: true,
    };
}
