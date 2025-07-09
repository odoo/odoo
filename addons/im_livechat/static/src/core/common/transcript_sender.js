import { isValidEmail } from "@im_livechat/core/common/misc";
import { Component, onWillUpdateProps, useEffect, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread}
 * @extends {Component<Props, Env>}
 */
export class TranscriptSender extends Component {
    static template = "im_livechat.TranscriptSender";
    static props = ["thread", "disableOnSend?"];

    STATUS = Object.freeze({
        IDLE: "idle",
        SENDING: "sending",
        SENT: "sent",
        FAILED: "failed",
    });

    setup() {
        this.isValidEmail = isValidEmail;
        this.state = useState({
            email: this.props.thread.livechatVisitorMember?.partner_id?.email || this.props.thread.livechatVisitorMember?.guest_id?.email,
            status: this.STATUS.IDLE,
        });
        onWillUpdateProps((newProps) => {
            if (this.props.thread?.notEq(newProps.thread)) {
                this.state.email = newProps.thread.livechatVisitorMember?.partner_id?.email || newProps.thread.livechatVisitorMember?.guest_id?.email;
                this.state.status = this.STATUS.IDLE;
            }
        });
        useEffect(
            () => {
                this.state.status = this.STATUS.IDLE;
            },
            () => [this.state.email]
        );
    }

    get isButtonDisabled() {
        return (
            this.isInputDisabled ||
            this.state.status === this.STATUS.SENT ||
            !this.isValidEmail(this.state.email)
        );
    }

    get isInputDisabled() {
        return (
            this.state.status === this.STATUS.SENDING ||
            (this.props.disableOnSend &&
                [this.STATUS.SENDING, this.STATUS.SENT].includes(this.state.status))
        );
    }

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        if (ev.key == "Enter" && !this.isButtonDisabled) {
            this.onClickSend();
        }
    }

    clear() {
        this.state.status = this.STATUS.IDLE;
        this.state.email = "";
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
