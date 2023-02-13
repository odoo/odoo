/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { _lt } from "@web/core/l10n/translation";

export class ConfirmPopup extends AbstractAwaitablePopup {
    static template = "ConfirmPopup";
    static defaultProps = {
        confirmText: _lt("Ok"),
        cancelText: _lt("Cancel"),
        title: _lt("Confirm ?"),
        body: "",
    };
}
