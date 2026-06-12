import { props, proxy, t } from "@odoo/owl";
import {
    ConfirmationDialog,
    confirmationDialogProps,
} from "@web/core/confirmation_dialog/confirmation_dialog";

export class InputConfirmationDialog extends ConfirmationDialog {
    static template = "html_builder.InputConfirmationDialog";

    props = props({
        ...confirmationDialogProps,
        inputLabel: t.string().optional(),
        defaultValue: t.string().optional(),
    });

    setup() {
        super.setup();
        this.inputState = proxy({
            value: this.props.defaultValue,
        });
    }

    execButton(callback) {
        return super.execButton((...args) => callback?.(...args, this.inputState.value));
    }
}
