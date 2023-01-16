/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { _lt } from "@web/core/l10n/translation";

export class AlertPopup extends AbstractAwaitablePopup {
    static template = "AlertPopup";
    static defaultProps = {
        confirmText: _lt("Ok"),
        title: "",
        body: "",
        cancelKey: false,
    };
}
