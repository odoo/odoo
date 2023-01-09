/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
import { _lt } from "@web/core/l10n/translation";

// formerly OrderImportPopupWidget
class OrderImportPopup extends AbstractAwaitablePopup {
    get unpaidSkipped() {
        return (
            (this.props.report.unpaid_skipped_existing || 0) +
            (this.props.report.unpaid_skipped_session || 0)
        );
    }
    getPayload() {}
}
OrderImportPopup.template = "OrderImportPopup";
OrderImportPopup.defaultProps = {
    confirmText: _lt("Ok"),
    cancelKey: false,
    body: "",
};

Registries.Component.add(OrderImportPopup);

export default OrderImportPopup;
