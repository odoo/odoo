import { onMounted, useProps, t } from "@odoo/owl";
import {
    ConfirmationDialog,
    confirmationDialogProps,
} from "@web/core/confirmation_dialog/confirmation_dialog";

export class InputConfirmationDialog extends ConfirmationDialog {
    props = useProps({
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
        onMounted(() => {
            if (!this.modalRef()) return;
            this.inputEl = this.modalRef().querySelector("input");
            for (const input of this.modalRef().querySelectorAll("input[default-checked]")) {
                input.checked = true;
            }
            if (this.inputEl) {
                this.inputEl.focus();
                this.inputEl.addEventListener("keydown", onKeydown);
                this.inputEl.addEventListener("input", onInput);
            }
        });
    }

    _confirm() {
        this.execButton(() => this.props.confirm({ inputEl: this.inputEl }));
    }
}
