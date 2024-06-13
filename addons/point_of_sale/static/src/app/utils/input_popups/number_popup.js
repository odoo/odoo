import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { Numpad, buttonsType } from "@point_of_sale/app/generic_components/numpad/numpad";

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
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        title: _t("Confirm?"),
        startingValue: "",
        formatDisplayedValue: (x) => x,
        feedback: () => false,
    };

    setup() {
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use();
        this.state = useState({
            buffer: this.props.startingValue,
        });
        useBus(this.numberBuffer, "buffer-update", ({ detail: value }) => {
            this.state.buffer = value;
        });
    }
    confirm() {
        this.props.getPayload(this.state.buffer || "0");
        this.props.close();
    }
}
