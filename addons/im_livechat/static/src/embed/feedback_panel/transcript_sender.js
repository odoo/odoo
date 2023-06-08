/* @odoo-module */

import { isValidEmail } from "@im_livechat/embed/core/misc";

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread}
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
    }

    async onClickSend() {
        this.state.status = this.STATUS.SENDING;
        try {
            await this.livechatService.sendTranscript(this.props.thread.uuid, this.state.email);
            this.state.status = this.STATUS.SENT;
        } catch {
            this.state.status = this.STATUS.FAILED;
        }
    }
}
