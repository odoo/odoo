/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    inputText(val) {
        return [
            {
                content: `input text '${val}'`,
                trigger: `.modal-dialog .popup-textinput input`,
                run: `text ${val}`,
            },
        ];
    }
    clickConfirm() {
        return [
            {
                content: "confirm text input popup",
                trigger: ".modal-dialog .confirm",
            },
        ];
    }
}

class Check {
    isShown() {
        return [
            {
                content: "text input popup is shown",
                trigger: ".modal-dialog .popup-textinput",
                run: () => {},
            },
        ];
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("TextInputPopup", Do, Check));
