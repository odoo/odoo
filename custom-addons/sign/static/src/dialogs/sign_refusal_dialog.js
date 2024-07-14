/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ThankYouDialog } from "./thank_you_dialog";

export class SignRefusalDialog extends Component {
    setup() {
        this.refuseReasonEl = useRef("refuse-reason");
        this.refuseButton = useRef("refuse-button");
        this.rpc = useService("rpc");
        this.dialog = useService("dialog");
        this.signInfo = useService("signInfo");
    }

    get dialogProps() {
        return {
            size: "md",
            title: _t("Refuse Document"),
        };
    }

    checkForChanges() {
        const value = this.refuseReasonEl.el.value.trim();
        this.refuseButton.el.disabled = value.length === 0 ? "disabled" : "";
    }

    async refuse() {
        const reason = this.refuseReasonEl.el.value;
        const route = `/sign/refuse/${this.signInfo.get("documentId")}/${this.signInfo.get(
            "signRequestItemToken"
        )}`;
        const params = {
            refusal_reason: reason,
        };
        const response = await this.rpc(route, params);
        if (!response) {
            this.dialog.add(
                AlertDialog,
                {
                    body: _t("Sorry, you cannot refuse this document"),
                },
                {
                    onClose: () => window.location.reload(),
                }
            );
        }
        this.dialog.add(ThankYouDialog, {
            subtitle: _t("The document has been refused"),
            message: _t(
                "We'll send an email to warn other contacts in copy & signers with the reason you provided."
            ),
        });

        this.props.close();
    }
}

SignRefusalDialog.template = "sign.SignRefusalDialog";

SignRefusalDialog.components = {
    Dialog,
};

SignRefusalDialog.props = {
    close: Function,
};
