/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { isValidEmail } from "../core/misc";
import { _t } from "@web/core/l10n/translation";

const STATUS = Object.freeze({
    SENDING: "sending",
    FAILED: "failed",
    SENT: "sent",
    IDLE: "idle",
});

export class TranscriptSender extends Component {
    static template = "im_livechat.TranscriptSender";
    static props = ["thread"];

    setup() {
        this.livechatService = useService("im_livechat.livechat");
        this.state = useState({
            email: "",
            status: STATUS.IDLE,
        });
    }

    async onClickSend() {
        this.state.status = STATUS.SENDING;
        try {
            await this.livechatService.sendTranscript(this.props.thread.uuid, this.state.email);
            this.state.status = STATUS.SENT;
        } catch {
            this.state.status = STATUS.FAILED;
        }
    }

    get buttonDisabled() {
        return (
            !this.state.email ||
            !isValidEmail(this.state.email) ||
            [STATUS.SENDING, STATUS.SENT].includes(this.state.status)
        );
    }

    get inputDisabled() {
        return [STATUS.SENDING, STATUS.SENT].includes(this.state.status);
    }

    get hint() {
        switch (this.state.status) {
            case STATUS.SENT:
                return _t("The conversation was sent.");
            case STATUS.FAILED:
                return _t("An error occurred. Please try again.");
            default:
                return _t("Receive a copy of this conversation.");
        }
    }

    get icon() {
        switch (this.state.status) {
            case STATUS.SENDING:
                return "fa-spinner fa-spin";
            case STATUS.SENT:
                return "fa-check";
            case STATUS.IDLE:
                return "fa-paper-plane";
            case STATUS.FAILED:
                return "fa-repeat";
            default:
                return "";
        }
    }
}
