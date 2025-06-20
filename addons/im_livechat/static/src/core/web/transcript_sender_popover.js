import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { isValidEmail } from "../common/misc";

export class TranscriptSenderPopover extends Component {
    static components = { ActionPanel };
    static template = "im_livechat.TranscriptSenderPopover";
    static props = ["thread", "close"];

    STATUS = Object.freeze({
        IDLE: "idle",
        SENDING: "sending",
        SENT: "sent",
        FAILED: "failed",
    });

    setup() {
        this.isValidEmail = isValidEmail;
        useAutofocus();
        this.notificationService = useService("notification");
        this.state = useState({
            email: this.props.thread.correspondent.persona.email,
            status: this.STATUS.IDLE,
        });
    }

    get isButtonDisabled() {
        return (
            !this.state.email ||
            !this.isValidEmail(this.state.email) ||
            [this.STATUS.SENDING, this.STATUS.SENT].includes(this.state.status)
        );
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        if (ev.key == "Enter" && !this.isButtonDisabled) {
            this.onClickSend();
        }
    }

    async onClickSend() {
        this.state.status = this.STATUS.SENDING;
        try {
            await rpc("/im_livechat/email_livechat_transcript", {
                channel_id: this.props.thread.id,
                email: this.state.email,
            });
            this.state.status = this.STATUS.SENT;
            this.notificationService.add(_t("Conversation sent."), { type: "success" });
            this.props.close();
        } catch {
            this.state.status = this.STATUS.FAILED;
        }
    }
}
