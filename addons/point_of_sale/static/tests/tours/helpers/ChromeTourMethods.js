/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    confirmPopup() {
        return [
            {
                content: "confirm popup",
                trigger: ".popups .modal-dialog .button.confirm",
            },
        ];
    }
    clickTicketButton() {
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
    clickMenuButton() {
        return [
            {
                content: "Click on the menu button",
                trigger: ".menu-button",
            },
        ];
    }
    closeSession() {
        return [
            ...this.clickMenuButton(),
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
}

class Check {
    isCashMoveButtonHidden() {
        return [
            {
                extraTrigger: ".pos-topheader",
                trigger: ".pos-topheader:not(:contains(Cash In/Out))",
                run: () => {},
            },
        ];
    }

    isCashMoveButtonShown() {
        return [
            {
                trigger: ".pos-topheader:contains(Cash In/Out)",
                run: () => {},
            },
        ];
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("Chrome", Do, Check));
