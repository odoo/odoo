/** @odoo-module */
import core from "web.core";
var _t = core._t;

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { numberBuffer } from "@point_of_sale/js/Misc/NumberBuffer";
import { useListener } from "@web/core/utils/hooks";

import { Draggable } from "../Misc/Draggable";

const { useState } = owl;

export class NumberPopup extends AbstractAwaitablePopup {
    static components = { Draggable };
    static template = "NumberPopup";
    static defaultProps = {
        confirmText: _t("Confirm"),
        cancelText: _t("Discard"),
        title: _t("Confirm ?"),
        body: "",
        cheap: false,
        startingValue: null,
        isPassword: false,
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
        useListener("accept-input", this.confirm);
        useListener("close-this-popup", this.cancel);
        let startingBuffer = "";
        if (typeof this.props.startingValue === "number" && this.props.startingValue > 0) {
            startingBuffer = this.props.startingValue
                .toString()
                .replace(".", this.decimalSeparator);
        }
        this.state = useState({ buffer: startingBuffer, toStartOver: this.props.isInputSelected });
        numberBuffer.use({
            nonKeyboardInputEvent: "numpad-click-input",
            triggerAtEnter: "accept-input",
            triggerAtEscape: "close-this-popup",
            state: this.state,
        });
    }
    get decimalSeparator() {
        return this.env._t.database.parameters.decimal_point;
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
        if (numberBuffer.get()) {
            super.confirm();
        }
    }
    sendInput(key) {
        this.trigger("numpad-click-input", { key });
    }
    getPayload() {
        return numberBuffer.get();
    }
}
