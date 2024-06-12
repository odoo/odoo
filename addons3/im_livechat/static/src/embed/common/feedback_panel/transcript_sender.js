/* @odoo-module */

import { isValidEmail } from "@im_livechat/embed/common/misc";

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

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
        this.rpc = useService("rpc");
        this.state = useState({
            email: "",
            status: this.STATUS.IDLE,
        });
    }

    async onClickSend() {
        this.state.status = this.STATUS.SENDING;
        try {
            await this.rpc("/im_livechat/email_livechat_transcript", {
                uuid: this.props.thread.uuid,
                email: this.state.email,
            });
            this.state.status = this.STATUS.SENT;
        } catch {
            this.state.status = this.STATUS.FAILED;
        }
    }
}
