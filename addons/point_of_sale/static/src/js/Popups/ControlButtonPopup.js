/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { _lt } from "@web/core/l10n/translation";

export class ControlButtonPopup extends AbstractAwaitablePopup {
    static template = "ControlButtonPopup";
    static defaultProps = {
        cancelText: _lt("Back"),
        confirmKey: false,
    };
    static props = {
        ...AbstractAwaitablePopup.props,
        controlButtons: Object,
        cancelText: { type: String, optional: true },
    };
    /**
     * @param {Object} props
     * @param {string} props.startingValue
     */
    setup() {
        super.setup();
        this.controlButtons = this.props.controlButtons;
    }
}
