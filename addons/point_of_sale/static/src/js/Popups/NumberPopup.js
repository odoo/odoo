/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { useService } from "@web/core/utils/hooks";
import { useState, useRef, onMounted } from "@odoo/owl";

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
        nbrDecimal: 0,
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
        let startingPayload = null;
        if (typeof this.props.startingValue === "number" && this.props.startingValue > 0) {
            startingBuffer = this.props.startingValue
                .toFixed(this.props.nbrDecimal)
                .toString()
                .replace(".", this.decimalSeparator);
            startingPayload = this.props.startingValue.toFixed(this.props.nbrDecimal);
        }
        this.state = useState({
            buffer: startingBuffer,
            toStartOver: this.props.isInputSelected,
            payload: startingPayload,
        });
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use({
            triggerAtEnter: () => this.confirm(),
            triggerAtEscape: () => this.cancel(),
            state: this.state,
        });
        this.inputRef = useRef("input");
        onMounted(this.onMounted);
    }
    onMounted() {
        if (this.inputRef.el) {
            this.inputRef.el.focus();
        }
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
        if (this.numberBuffer.get() || this.state.payload) {
            super.confirm();
        }
    }
    sendInput(key) {
        this.numberBuffer.sendKey(key);
    }
    getPayload() {
        let startingPayload = null;
        if (typeof this.props.startingValue === "number" && this.props.startingValue > 0) {
            startingPayload = this.props.startingValue.toFixed(this.props.nbrDecimal);
        }
        if (this.state.payload != startingPayload) {
            return this.state.payload;
        }
        return this.numberBuffer.get();
    }
    isMobile() {
        return window.innerWidth <= 768;
    }
}
