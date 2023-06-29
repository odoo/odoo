/** @odoo-module */

import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";
import { Do } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";

class DoExt extends Do {
    backToFloor() {
        return [
            {
                content: "back to floor",
                trigger: ".floor-button",
            },
        ];
    }
}

class Check {
    isSyncStatusPending() {
        return [
            {
                trigger: ".pos-topheader .pos-rightheader .status-buttons .oe_status:has(.js_msg)",
                run: () => {},
            },
        ];
    }
    isSyncStatusConnected() {
        return [
            {
                trigger:
                    ".pos-topheader .pos-rightheader .status-buttons .oe_status:has(.js_connected)",
                run: () => {},
            },
        ];
    }
}

class Execute {}

// FIXME: this is a horrible hack to export an object as named exports.
// eslint-disable-next-line no-undef
Object.assign(__exports, createTourMethods("Chrome", DoExt, Check, Execute));
