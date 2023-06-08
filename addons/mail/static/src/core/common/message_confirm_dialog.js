/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageConfirmDialog extends Component {
    static components = { Dialog };
    static props = [
        "close",
        "confirmColor?",
        "confirmText?",
        "message",
        "messageComponent",
        "prompt",
        "size?",
        "title?",
        "onConfirm",
    ];
    static defaultProps = {
        confirmColor: "btn-primary",
        confirmText: _t("Confirm"),
        size: "xl",
        title: _t("Confirmation"),
    };
    static template = "mail.MessageConfirmDialog";

    setup() {
        /** @type {import("@mail/core/common/message_service").MessageService} */
        this.messageService = useState(useService("mail.message"));
    }

    onClickConfirm() {
        this.props.onConfirm();
        this.props.close();
    }
}
