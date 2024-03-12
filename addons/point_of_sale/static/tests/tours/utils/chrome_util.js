/** @odoo-module */
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";

export function confirmPopup() {
    return [Dialog.confirm()];
}
export function clickTicketButton() {
    return [
        {
            trigger: ".pos-topheader .ticket-button",
        },
        {
            trigger: ".screen.ticket-screen",
            run: () => {},
        },
    ];
}
export function clickMenuButton() {
    return {
        content: "Click on the menu button",
        trigger: ".menu-button",
    };
}
export function clickMenuOption(name) {
    return [
        clickMenuButton(),
        {
            content: `click on something in the burger menu`,
            trigger: `a.dropdown-item:contains(${name})`,
        },
    ];
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
export function isCashMoveButtonShown() {
    return [
        {
            trigger: ".pos-topheader:contains(Cash In/Out)",
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
