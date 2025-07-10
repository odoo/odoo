/** @odoo-module */
import { negate } from "@point_of_sale/../tests/tours/helpers/utils";

export function confirmPopup() {
    return [
        {
            content: "confirm popup",
            trigger: ".popups .modal-dialog .button.confirm",
        },
    ];
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
    return [
        {
            content: "Click on the menu button",
            trigger: ".menu-button",
        },
    ];
}
export function closeSession() {
    return [
        ...clickMenuButton(),
        {
            content: "click on the close session menu button",
            trigger: ".close-button",
        },
        {
            content: "click on the close session popup button",
            trigger: ".close-pos-popup .footer .button.highlight",
        },
        {
            content: "check that the session is closed without error",
            trigger: ".o_web_client",
            isCheck: true,
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
export function freezeDateTime(ms) {
    return [
        {
            trigger: "body",
            run: () => {
                luxon.DateTime.now = () => luxon.DateTime.fromMillis(ms);
            },
        },
    ];
}
export function isSynced() {
    return {
        trigger: negate(".fa-spin"),
    }
}
export function endTour() {
    return {
        content: "Last tour step that avoids error mentioned in commit 443c209",
        trigger: "body",
        isCheck: true,
    };
}
