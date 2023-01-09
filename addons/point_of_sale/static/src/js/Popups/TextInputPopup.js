/** @odoo-module */

import AbstractAwaitablePopup from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import Registries from "@point_of_sale/js/Registries";
import { _lt } from "@web/core/l10n/translation";

const { onMounted, useRef, useState } = owl;

// formerly TextInputPopupWidget
class TextInputPopup extends AbstractAwaitablePopup {
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
TextInputPopup.template = "TextInputPopup";
TextInputPopup.defaultProps = {
    confirmText: _lt("Confirm"),
    cancelText: _lt("Discard"),
    title: "",
    body: "",
    startingValue: "",
    placeholder: "",
};

Registries.Component.add(TextInputPopup);

export default TextInputPopup;
