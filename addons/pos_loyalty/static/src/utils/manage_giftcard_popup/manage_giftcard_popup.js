import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class ManageGiftCardPopup extends Component {
    static template = "pos_loyalty.ManageGiftCardPopup";
    static components = { Dialog };
    static props = {
        title: String,
        placeholder: { type: String, optional: true },
        rows: { type: Number, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        startingValue: "",
        placeholder: "",
        rows: 1,
    };

    setup() {
        this.state = useState({
            inputValue: this.props.startingValue,
            amountValue: "",
            error: false,
            amountError: false,
        });
        this.inputRef = useRef("input");
        this.amountInputRef = useRef("amountInput");
        onMounted(this.onMounted);
    }

    onMounted() {
        this.inputRef.el.focus();
    }

    addBalance() {
        if (!this.validateCode()) {
            return;
        }
        this.props.getPayload(this.state.inputValue, parseFloat(this.state.amountValue));
        this.props.close();
    }

    close() {
        this.props.close();
    }

    validateCode() {
        const { inputValue, amountValue } = this.state;
        if (inputValue.trim() === "") {
            this.state.error = true;
            return false;
        }
        if (amountValue.trim() === "") {
            this.state.amountError = true;
            return false;
        }
        return true;
    }
}
