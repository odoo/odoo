/* @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageConfirmDialog extends Component {
    static components = { Dialog };
    static props = ["close", "message", "messageComponent", "prompt", "onConfirm"];
    static template = "mail.MessageConfirmDialog";

    setup() {
        /** @type {import("@mail/core/message_service").MessageService} */
        this.messageService = useState(useService("mail.message"));
        this.title = _t("Confirmation");
    }

    onClickConfirm() {
        this.props.onConfirm();
        this.props.close();
    }
}
