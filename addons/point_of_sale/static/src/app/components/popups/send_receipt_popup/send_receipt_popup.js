import { useState } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { isValidEmail } from "@point_of_sale/utils";

export class SendReceiptPopup extends Component {
    static template = "point_of_sale.SendReceiptPopup";
    static components = { Dialog };
    static props = {
        order: Object,
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.renderer = useService("renderer");
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        const partner = this.order.getPartner();
        const email = partner?.invoice_emails || partner?.email || "";
        this.state = useState({
            email: email,
            phone: partner?.phone || "",
        });
        this.sendReceipt = useTrackedAsync(this._sendReceiptToCustomer.bind(this));
    }

    actionSendReceiptOnEmail() {
        this.sendReceipt.call({
            action: "action_send_receipt",
            destination: this.state.email,
            name: "Email",
        });
    }

    get order() {
        return this.props.order;
    }

    get isValidEmail() {
        return isValidEmail(this.state.email);
    }

    get isValidPhone() {
        return this.state.phone && /^\+?[()\d\s-.]{8,18}$/.test(this.state.phone);
    }

    async _sendReceiptToCustomer({ action, destination }) {
        if (!this.order.isSynced) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Unsynced order"),
                body: _t(
                    "This order is not yet synced to server. Make sure it is synced then try again."
                ),
                showReloadButton: true,
            });
            return Promise.reject();
        }
        await this.pos.data.call("pos.order", action, [[this.order.id], destination]);
    }

    get sendList() {
        const list = [
            {
                inputClass: "send-receipt-email-input",
                buttons: [
                    {
                        click: () => this.actionSendReceiptOnEmail(),
                        status:
                            this.sendReceipt.lastArgs?.[0]?.name == "Email" &&
                            this.sendReceipt.status,
                        icon: "fa-paper-plane",
                        disabled: () => !this.isValidEmail,
                    },
                ],
                placeholder: _t("Email"),
                model: "email",
                show: () => true,
            },
            {
                inputClass: "send-receipt-phone-input",
                buttons: [],
                placeholder: _t("Phone"),
                model: "phone",
                show: () => this.showPhoneInput(),
            },
        ];
        return list;
    }

    showPhoneInput() {
        return false;
    }

    actionSendReceiptOnPhone() {
        return false;
    }
}
