import { useLayoutEffect } from "@web/owl2/utils";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class InputConfirmationDialog extends ConfirmationDialog {
    static props = {
        ...ConfirmationDialog.props,
        onInput: { type: Function, optional: true },
    };
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
