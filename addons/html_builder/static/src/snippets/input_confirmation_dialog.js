import { useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class InputConfirmationDialog extends ConfirmationDialog {
    static template = "html_builder.InputConfirmationDialog";

    static props = {
        ...ConfirmationDialog.props,
        inputLabel: { type: String, optional: true },
        defaultValue: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.inputState = useState({
            value: this.props.defaultValue,
        });
    }

    execButton(callback) {
        return super.execButton((...args) => callback?.(...args, this.inputState.value));
    }
}
