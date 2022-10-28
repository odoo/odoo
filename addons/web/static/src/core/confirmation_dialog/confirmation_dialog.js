/** @odoo-module */

import { Dialog } from "../dialog/dialog";
import { _lt } from "../l10n/translation";
import { useChildRef } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class ConfirmationDialog extends Component {
    setup() {
        this.env.dialogData.close = () => this._cancel();
        this.modalRef = useChildRef();
        this.isConfirmedOrCancelled = false; // ensures we do not confirm and/or cancel twice
    }
    async _cancel() {
        if (this.isConfirmedOrCancelled) {
            return;
        }
        this.isConfirmedOrCancelled = true;
        this.disableButtons();
        if (this.props.cancel) {
            try {
                await this.props.cancel();
            } catch (e) {
                this.props.close();
                throw e;
            }
        }
        this.props.close();
    }
    async _confirm() {
        if (this.isConfirmedOrCancelled) {
            return;
        }
        this.isConfirmedOrCancelled = true;
        this.disableButtons();
        if (this.props.confirm) {
            try {
                await this.props.confirm();
            } catch (e) {
                this.props.close();
                throw e;
            }
        }
        this.props.close();
    }
    disableButtons() {
        if (!this.modalRef.el) {
            return; // safety belt for stable versions
        }
        for (const button of [...this.modalRef.el.querySelectorAll(".modal-footer button")]) {
            button.disabled = true;
        }
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
    cancel: { type: Function, optional: true },
    cancelLabel: { type: String, optional: true },
};
ConfirmationDialog.defaultProps = {
    confirmLabel: _lt("Ok"),
    cancelLabel: _lt("Cancel"),
    title: _lt("Confirmation"),
};

export class AlertDialog extends ConfirmationDialog {}
AlertDialog.template = "web.AlertDialog";
AlertDialog.props = {
    ...ConfirmationDialog.props,
    contentClass: { type: String, optional: true },
};
AlertDialog.defaultProps = {
    ...ConfirmationDialog.defaultProps,
    title: _lt("Alert"),
};
