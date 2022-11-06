/** @odoo-module */

import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { useMessaging } from "../messaging_hook";
import { useEmojiPicker, loadEmojiData } from "./emoji_picker";

export class Composer extends Component {
    static template = "mail.composer";
    static props = ["threadId", "autofocus?", "onPostCallback?", "mode?", "placeholder?", "type?"];
    static defaultProps = { type: "message"};

    setup() {
        this.messaging = useMessaging();
        this.ref = useRef("textarea");
        this.state = useState({ value: "", autofocus: 0 });
        useEmojiPicker("emoji-picker", (str) => this.addEmoji(str));
        useEffect(
            (focus) => {
                if (focus && this.ref.el) {
                    this.ref.el.focus();
                }
            },
            () => [this.props.autofocus + this.state.autofocus, this.props.placeholder]
        );
    }

    onKeydown(ev) {
        loadEmojiData();
        if (ev.keyCode === 13) {
            ev.preventDefault(); // to prevent useless return
            this.sendMessage();
        }
    }

    async sendMessage() {
        const el = this.ref.el;
        if (el.value.trim()) {
            const prom = this.messaging.postMessage(this.props.threadId, el.value, this.props.type === "note");
            await prom;
            if (this.props.onPostCallback) {
                this.props.onPostCallback();
            }
        }
        this.state.value = "";
        el.focus();
    }

    addEmoji(str) {
        this.state.value += str;
        this.state.autofocus++;
    }
}
