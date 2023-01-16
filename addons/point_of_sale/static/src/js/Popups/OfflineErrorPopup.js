/** @odoo-module */

import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { _lt } from "@web/core/l10n/translation";

import { Draggable } from "../Misc/Draggable";

/**
 * This is a special kind of error popup as it introduces
 * an option to not show it again.
 */
export class OfflineErrorPopup extends ErrorPopup {
    static components = { Draggable };
    static template = "OfflineErrorPopup";
    static dontShow = false;
    static defaultProps = {
        confirmText: _lt("Ok"),
        cancelText: _lt("Cancel"),
        title: _lt("Offline Error"),
        body: _lt("Either the server is inaccessible or browser is not connected online."),
    };

    dontShowAgain() {
        this.constructor.dontShow = true;
        this.cancel();
    }
}
