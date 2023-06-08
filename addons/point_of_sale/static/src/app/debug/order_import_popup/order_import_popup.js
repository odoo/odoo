/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _lt } from "@web/core/l10n/translation";

export class OrderImportPopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.OrderImportPopup";
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
