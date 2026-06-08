import { props, t } from "@odoo/owl";
import { useLayoutEffect } from "@web/owl2/utils";
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
        useLayoutEffect(
            (inputEl) => {
                this.inputEl = inputEl;
                if (this.inputEl) {
                    this.inputEl.focus();
                    this.inputEl.addEventListener("keydown", onKeydown);
                    this.inputEl.addEventListener("input", onInput);
                    return () => {
                        this.inputEl.removeEventListener("keydown", onKeydown);
                        this.inputEl.removeEventListener("input", onInput);
                    };
                }
            },
            () => [this.modalRef.el?.querySelector("input")]
        );
    }

    _confirm() {
        this.execButton(() => this.props.confirm({ inputEl: this.inputEl }));
    }
}
