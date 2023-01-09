/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
import { _lt } from "@web/core/l10n/translation";

// formerly ErrorPopupWidget
class ErrorPopup extends AbstractAwaitablePopup {
    setup() {
        super.setup();
        owl.onMounted(this.onMounted);
    }
    onMounted() {
        this.playSound("error");
    }
}
ErrorPopup.template = "ErrorPopup";
ErrorPopup.defaultProps = {
    confirmText: _lt("Ok"),
    title: _lt("Error"),
    body: "",
    cancelKey: false,
};

Registries.Component.add(ErrorPopup);

export default ErrorPopup;
