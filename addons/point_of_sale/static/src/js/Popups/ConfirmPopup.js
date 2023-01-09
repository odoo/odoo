/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
import { _lt } from "@web/core/l10n/translation";

// formerly ConfirmPopupWidget
class ConfirmPopup extends AbstractAwaitablePopup {}
ConfirmPopup.template = "ConfirmPopup";
ConfirmPopup.defaultProps = {
    confirmText: _lt("Ok"),
    cancelText: _lt("Cancel"),
    title: _lt("Confirm ?"),
    body: "",
};

Registries.Component.add(ConfirmPopup);

export default ConfirmPopup;
