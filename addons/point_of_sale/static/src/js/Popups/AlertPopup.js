/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { _lt } from "@web/core/l10n/translation";

export class AlertPopup extends AbstractAwaitablePopup {
    static template = "AlertPopup";
    static defaultProps = {
        confirmText: _lt("Ok"),
        title: "",
        cancelKey: false,
    };
    static props = {
        ...AbstractAwaitablePopup.props,
        confirmText: { type: String, optional: true },
        cancelText: { type: String, optional: true },
        title: { type: String, optional: true },
        body: String,
    };
}
