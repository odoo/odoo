/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _lt } from "@web/core/l10n/translation";
import { onMounted, useRef, useState } from "@odoo/owl";

// IMPROVEMENT: This code is very similar to TextInputPopup.
//      Combining them would reduce the code.
export class TextAreaPopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.TextAreaPopup";
    static defaultProps = {
        confirmText: _lt("Add"),
        cancelText: _lt("Discard"),
        title: "",
        body: "",
    };

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
