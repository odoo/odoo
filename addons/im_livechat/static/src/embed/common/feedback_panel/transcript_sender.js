import { isValidEmail } from "@im_livechat/embed/common/misc";
import { rpcWithEnv } from "@mail/utils/common/misc";

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

let rpc;
/**
 * @typedef {Object} Props
 * @property {import("models").Thread}
 * @extends {Component<Props, Env>}
 */
export class TranscriptSender extends Component {
    static template = "im_livechat.TranscriptSender";
    static props = ["thread"];

    STATUS = Object.freeze({
        IDLE: "idle",
        SENDING: "sending",
        SENT: "sent",
        FAILED: "failed",
    });

    setup() {
        this.isValidEmail = isValidEmail;
        this.livechatService = useService("im_livechat.livechat");
        this.state = useState({
            email: "",
            status: this.STATUS.IDLE,
        });
        rpc = rpcWithEnv(this.env);
    }

    async onClickSend() {
        this.state.status = this.STATUS.SENDING;
        try {
            await rpc("/im_livechat/email_livechat_transcript", {
                channel_id: this.props.thread.id,
                email: this.state.email,
            });
            this.state.status = this.STATUS.SENT;
        } catch {
            this.state.status = this.STATUS.FAILED;
        }
    }
}
