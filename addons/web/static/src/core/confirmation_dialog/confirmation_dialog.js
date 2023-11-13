/** @odoo-module */

import { Dialog } from "../dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useChildRef } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export const deleteConfirmationMessage = _t(
    "Ready to make your record disappear into thin air? Are you sure?\n\
It will be gone forever!\n\n\
Think twice before you click that 'Delete' button!"
);

export class ConfirmationDialog extends Component {
    setup() {
        this.env.dialogData.dismiss = () => this._cancel();
        this.modalRef = useChildRef();
        this.isProcess = false;
    }

    async _cancel() {
        return this.execButton(this.props.cancel);
    }

    async _confirm() {
        return this.execButton(this.props.confirm);
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
ConfirmationDialog.template = "web.ConfirmationDialog";
ConfirmationDialog.components = { Dialog };
ConfirmationDialog.props = {
    close: Function,
    title: {
        validate: (m) => {
            return (
                typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
            );
        },
        optional: true,
    },
    body: String,
    confirm: { type: Function, optional: true },
    confirmLabel: { type: String, optional: true },
    confirmClass: { type: String, optional: true },
    cancel: { type: Function, optional: true },
    cancelLabel: { type: String, optional: true },
};
ConfirmationDialog.defaultProps = {
    confirmLabel: _t("Ok"),
    cancelLabel: _t("Cancel"),
    confirmClass: "btn-primary",
    title: _t("Confirmation"),
};

export class AlertDialog extends ConfirmationDialog {}
AlertDialog.template = "web.AlertDialog";
AlertDialog.props = {
    ...ConfirmationDialog.props,
    contentClass: { type: String, optional: true },
};
AlertDialog.defaultProps = {
    ...ConfirmationDialog.defaultProps,
    title: _t("Alert"),
};
