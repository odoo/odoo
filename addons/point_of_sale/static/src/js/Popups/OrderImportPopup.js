/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { _lt } from "@web/core/l10n/translation";

import { Draggable } from "../Misc/Draggable";

// formerly OrderImportPopupWidget
export class OrderImportPopup extends AbstractAwaitablePopup {
    static components = { Draggable };
    static template = "OrderImportPopup";
    static defaultProps = {
        confirmText: _lt("Ok"),
        cancelKey: false,
        body: "",
    };

    get unpaidSkipped() {
        return (
            (this.props.report.unpaid_skipped_existing || 0) +
            (this.props.report.unpaid_skipped_session || 0)
        );
    }
    getPayload() {}
}
