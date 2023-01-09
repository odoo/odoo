/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    clickItem(name) {
        return [
            {
                content: `click selection '${name}'`,
                trigger: `.selection-item:contains("${name}")`,
            },
        ];
    }
}

class Check {
    hasSelectionItem(name) {
        return [
            {
                content: `selection popup has '${name}'`,
                trigger: `.selection-item:contains("${name}")`,
                run: () => {},
            },
        ];
    }
    isShown() {
        return [
            {
                content: "selection popup is shown",
                trigger: ".modal-dialog .popup-selection",
                run: () => {},
            },
        ];
    }
}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("SelectionPopup", Do, Check));
