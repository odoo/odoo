/** @odoo-module native */
import { useEffect } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { ConfirmationDialog } from "@web/ui/dialog";

const log = makeLogger("portal.input_dialog");

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
            if (ev.key === "Enter" && !ev.isComposing) {
                ev.preventDefault();
                this.confirm();
            }
        };
        useEffect(
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
            () => [this.modalRef.el?.querySelector("input")],
        );
    }

    confirm() {
        return this.execButton(() => {
            const validationTarget = this.inputEl?.form || this.inputEl;
            if (validationTarget && !validationTarget.reportValidity()) {
                log.logic("confirmation blocked by invalid input");
                return false;
            }
            return this.props.confirm?.({ inputEl: this.inputEl });
        });
    }
}
