/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
import { _lt } from "@web/core/l10n/translation";

class ControlButtonPopup extends AbstractAwaitablePopup {
    /**
     * @param {Object} props
     * @param {string} props.startingValue
     */
    setup() {
        super.setup();
        this.controlButtons = this.props.controlButtons;
    }
}
ControlButtonPopup.template = "ControlButtonPopup";
ControlButtonPopup.defaultProps = {
    cancelText: _lt("Back"),
    controlButtons: [],
    confirmKey: false,
};

Registries.Component.add(ControlButtonPopup);

export default ControlButtonPopup;
