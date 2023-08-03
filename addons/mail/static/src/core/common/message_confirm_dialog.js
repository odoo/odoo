/* @odoo-module */

import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

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

    onClickConfirm() {
        this.props.onConfirm();
        this.props.close();
    }
}
