/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

export class NumberPopup extends AbstractAwaitablePopup {
    static template = "NumberPopup";
    static defaultProps = {
        confirmText: _t("Confirm"),
        cancelText: _t("Discard"),
        title: _t("Confirm?"),
        subtitle: "",
        body: "",
        cheap: false,
        startingValue: null,
        isPassword: false,
        inputSuffix: "",
        getInputBufferReminder: () => false,
    };

    /**
     * @param {Object} props
     * @param {Boolean} props.isPassword Show password popup.
     * @param {number|null} props.startingValue Starting value of the popup.
     * @param {Boolean} props.isInputSelected Input is highlighted and will reset upon a change.
     *
     * Resolve to { confirmed, payload } when used with showPopup method.
     * @confirmed {Boolean}
     * @payload {String}
     */
    setup() {
        super.setup();
        this.localization = useService("localization");
        let startingBuffer = "";
        if (typeof this.props.startingValue === "number" && this.props.startingValue > 0) {
            startingBuffer = this.props.startingValue
                .toString()
                .replace(".", this.decimalSeparator);
        }
        this.state = useState({ buffer: startingBuffer, toStartOver: this.props.isInputSelected });
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use({
            triggerAtEnter: () => this.confirm(),
            triggerAtEscape: () => this.cancel(),
            state: this.state,
        });
    }
    get decimalSeparator() {
        return this.localization.decimalPoint;
    }
    get inputBuffer() {
        if (this.state.buffer === null) {
            return "";
        }
        if (this.props.isPassword) {
            return this.state.buffer.replace(/./g, "•");
        } else {
            return this.state.buffer;
        }
    }
    confirm(event) {
        if (this.numberBuffer.get()) {
            super.confirm();
        }
    }
    sendInput(key) {
        this.numberBuffer.sendKey(key);
    }
    getPayload() {
        return this.numberBuffer.get();
    }
}
