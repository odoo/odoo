import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { Numpad, buttonsType } from "@point_of_sale/app/components/numpad/numpad";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

export class NumberPopup extends Component {
    static template = "point_of_sale.NumberPopup";
    static components = { Numpad, Dialog };
    static props = {
        title: { type: String, optional: true },
        subtitle: { type: String, optional: true },
        buttons: { type: buttonsType, optional: true },
        startingValue: { type: [Number, String], optional: true },
        feedback: { type: Function, optional: true },
        formatDisplayedValue: { type: Function, optional: true },
        placeholder: { type: String, optional: true },
        isValid: { type: Function, optional: true },
        isValidFeedback: { type: Function, optional: true },
        isValidBlocking: { type: Boolean, optional: true },
        confirmButtonLabel: { type: String, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        title: _t("Confirm?"),
        startingValue: "",
        isValidBlocking: true,
        isValid: () => true,
        formatDisplayedValue: (x) => x,
        feedback: () => false,
    };

    setup() {
        this.state = useState({
            buffer: "",
        });
        this.props.placeholder = this.props.startingValue;
        useHotkey("enter", () => this.confirm());
    }
    confirm() {
        this.props.getPayload(this.state.buffer);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
