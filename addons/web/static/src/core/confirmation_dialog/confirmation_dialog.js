import { Dialog } from "../dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useChildRef } from "@web/core/utils/hooks";

import { Component, props, t } from "@odoo/owl";

export const deleteConfirmationMessage = _t(
    `Ready to make your record disappear into thin air? Are you sure? It will be gone forever!
    
Think twice before you click that 'Delete' button!`
);

const isValidTitle = (m) =>
    typeof m === "string" || (typeof m === "object" && typeof m.toString === "function");

export const confirmationDialogProps = {
    close: t.function(),
    title: t.customValidator(t.any(), isValidTitle).optional(_t("Confirmation")),
    size: t.string().optional("sm"),
    body: t.string().optional(),
    confirm: t.function().optional(),
    confirmLabel: t.string().optional(_t("Ok")),
    confirmClass: t.string().optional("btn-primary"),
    cancel: t.function().optional(),
    cancelLabel: t.string().optional(_t("Discard")),
    dismiss: t.function().optional(),
};

export class ConfirmationDialog extends Component {
    static template = "web.ConfirmationDialog";
    static components = { Dialog };
    props = props(confirmationDialogProps);

    setup() {
        this.env.dialogData.dismiss = () => this._dismiss();
        this.modalRef = useChildRef();
        this.isProcess = false;
    }

    async _cancel() {
        return this.execButton(this.props.cancel);
    }

    async _confirm() {
        return this.execButton(this.props.confirm);
    }

    async _dismiss() {
        return this.execButton(this.props.dismiss || this.props.cancel);
    }

    setButtonsDisabled(disabled) {
        this.isProcess = disabled;
        if (!this.modalRef.el) {
            return; // safety belt for stable versions
        }
        for (const button of [...this.modalRef.el.querySelectorAll(".modal-footer button")]) {
            button.disabled = disabled;
        }
    }

    async execButton(callback) {
        if (this.isProcess) {
            return;
        }
        this.setButtonsDisabled(true);
        if (callback) {
            let shouldClose;
            try {
                shouldClose = await callback();
            } catch (e) {
                this.props.close();
                throw e;
            }
            if (shouldClose === false) {
                this.setButtonsDisabled(false);
                return;
            }
        }
        this.props.close();
    }
}

export const alertDialogProps = {
    ...confirmationDialogProps,
    title: t.customValidator(t.any(), isValidTitle).optional(_t("Alert")),
    contentClass: t.string().optional(),
};

export class AlertDialog extends ConfirmationDialog {
    static template = "web.AlertDialog";
    props = props(alertDialogProps);
}
