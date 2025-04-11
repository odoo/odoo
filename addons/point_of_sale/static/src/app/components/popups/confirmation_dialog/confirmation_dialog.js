import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";

patch(ConfirmationDialog.prototype, {
    async _cancel() {
        this.props.getPayload && this.props.getPayload(false);
        return this.execButton(this.props.cancel);
    },
    async _confirm() {
        this.props.getPayload && this.props.getPayload(true);
        return this.execButton(this.props.confirm);
    },
    async _dismiss() {
        this.props.getPayload && this.props.getPayload(false);
        return this.execButton(this.props.dismiss || this.props.cancel);
    },
});

ConfirmationDialog.props = {
    ...ConfirmationDialog.props,
    getPayload: { type: Function, optional: true },
};

AlertDialog.props = {
    ...AlertDialog.props,
    getPayload: { type: Function, optional: true },
};
