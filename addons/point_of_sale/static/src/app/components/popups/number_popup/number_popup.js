import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { Numpad, buttonsType } from "@point_of_sale/app/components/numpad/numpad";

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
        this.buffer = useService("buffer_service");
        this.state = useState({
            buffer: this.props.startingValue || 0,
        });
        this.buffer.use({
            callback: (num) => (this.state.buffer = num),
            buffer: {
                value: 0,
                symbolStart: parseFloat(this.props.startingValue || 0),
            },
        });
    }

    confirm() {
        this.props.getPayload(this.state.buffer);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
