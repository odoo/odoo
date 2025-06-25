import { Dialog } from "../dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useChildRef } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export const deleteConfirmationMessage = _t(
    `Ready to make your record disappear into thin air? Are you sure?
It will be gone forever!

Think twice before you click that 'Delete' button!`
);

export class ConfirmationDialog extends Component {
    static template = "web.ConfirmationDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        title: {
            validate: (m) => {
                return (
                    typeof m === "string" ||
                    (typeof m === "object" && typeof m.toString === "function")
                );
            },
            optional: true,
        },
        body: { type: String, optional: true },
        confirm: { type: Function, optional: true },
        confirmLabel: { type: String, optional: true },
        confirmClass: { type: String, optional: true },
        cancel: { type: Function, optional: true },
        cancelLabel: { type: String, optional: true },
        dismiss: { type: Function, optional: true },
    };
    static defaultProps = {
        confirmLabel: _t("Ok"),
        cancelLabel: _t("Cancel"),
        confirmClass: "btn-primary",
        title: _t("Confirmation"),
    };

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

export class AlertDialog extends ConfirmationDialog {
    static template = "web.AlertDialog";
    static props = {
        ...ConfirmationDialog.props,
        contentClass: { type: String, optional: true },
    };
    static defaultProps = {
        ...ConfirmationDialog.defaultProps,
        title: _t("Alert"),
    };
}
