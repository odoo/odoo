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
                trigger: ".subwindow .ticket-screen",
                run: () => {},
            },
        ];
    }
}

class Check {
    isCashMoveButtonHidden() {
        return [
            {
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
