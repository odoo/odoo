/** @odoo-module */
import ErrorPopup from "point_of_sale.ErrorPopup";
import Registries from "point_of_sale.Registries";
import { _lt } from "@web/core/l10n/translation";

/**
 * This is a special kind of error popup as it introduces
 * an option to not show it again.
 */
export class OfflineErrorPopup extends ErrorPopup {
    dontShowAgain() {
        this.constructor.dontShow = true;
        this.cancel();
    }
}
OfflineErrorPopup.template = "OfflineErrorPopup";
OfflineErrorPopup.dontShow = false;
OfflineErrorPopup.defaultProps = {
    confirmText: _lt("Ok"),
    cancelText: _lt("Cancel"),
    title: _lt("Offline Error"),
    body: _lt("Either the server is inaccessible or browser is not connected online."),
};

Registries.Component.add(OfflineErrorPopup);
