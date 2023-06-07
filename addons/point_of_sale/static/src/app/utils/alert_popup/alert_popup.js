/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _lt } from "@web/core/l10n/translation";

export class AlertPopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.AlertPopup";
    static defaultProps = {
        confirmText: _lt("Ok"),
        title: "",
        body: "",
        cancelKey: false,
    };
}
