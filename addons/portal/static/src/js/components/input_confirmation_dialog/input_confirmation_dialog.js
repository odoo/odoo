import { onMounted, props, t, useListener } from "@odoo/owl";
import {
    ConfirmationDialog,
    confirmationDialogProps,
} from "@web/core/confirmation_dialog/confirmation_dialog";

export class InputConfirmationDialog extends ConfirmationDialog {
    props = props({
        ...confirmationDialogProps,
        onInput: t.function().optional(),
    });
    static template = "portal.InputConfirmationDialog";

    setup() {
        super.setup();

        const onInput = () => {
            if (this.props.onInput) {
                this.props.onInput({ inputEl: this.inputEl });
            }
        };
        const onKeydown = (ev) => {
            if (ev.key && ev.key.toLowerCase() === "enter") {
                ev.preventDefault();
                this._confirm();
            }
        };
        useListener(() => this.modalRef.el?.querySelector("input"), "keydown", onKeydown);
        useListener(() => this.modalRef.el?.querySelector("input"), "input", onInput);
        onMounted(() => {
            this.inputEl = this.modalRef.el?.querySelector("input");
            this.inputEl?.focus();
        });
    }

    _confirm() {
        this.execButton(() => this.props.confirm({ inputEl: this.inputEl }));
    }
}
