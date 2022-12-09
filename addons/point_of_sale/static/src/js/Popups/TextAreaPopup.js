/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
import { _lt } from "@web/core/l10n/translation";

const { onMounted, useRef, useState } = owl;

// formerly TextAreaPopupWidget
// IMPROVEMENT: This code is very similar to TextInputPopup.
//      Combining them would reduce the code.
class TextAreaPopup extends AbstractAwaitablePopup {
    /**
     * @param {Object} props
     * @param {string} props.startingValue
     */
    setup() {
        super.setup();
        this.state = useState({ inputValue: this.props.startingValue });
        this.inputRef = useRef("input");
        onMounted(this.onMounted);
    }
    onMounted() {
        this.inputRef.el.focus();
    }
    getPayload() {
        return this.state.inputValue;
    }
}
TextAreaPopup.template = "TextAreaPopup";
TextAreaPopup.defaultProps = {
    confirmText: _lt("Add"),
    cancelText: _lt("Discard"),
    title: "",
    body: "",
};

Registries.Component.add(TextAreaPopup);

export default TextAreaPopup;
