/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    clickConfirm() {
        return [
            {
                content: "click confirm button",
                trigger: ".popup-error .footer .cancel",
            },
        ];
    }
}

class Check {
    isShown() {
        return [
            {
                content: "error popup is shown",
                trigger: ".modal-dialog .popup-error",
                run: () => {},
            },
        ];
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("ErrorPopup", Do, Check));
