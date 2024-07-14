/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

export class ItsmeDialog extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.dialog = useService("dialog");
    }

    async onItsmeClick() {
        const { success, authorization_url, message } = await this.rpc(
            this.props.route,
            this.props.params
        );
        if (success) {
            if (authorization_url) {
                window.location.replace(authorization_url);
            } else {
                this.props.onSuccess();
            }
        } else {
            this.dialog.add(
                AlertDialog,
                {
                    body: message,
                },
                {
                    onClose: () => window.location.reload(),
                }
            );
        }
    }
}

ItsmeDialog.template = "sign_itsme.ItsmeDialog";
ItsmeDialog.components = {
    Dialog,
};

ItsmeDialog.props = {
    route: String,
    params: Object,
    onSuccess: Function,
    close: Function,
};
