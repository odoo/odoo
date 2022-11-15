/** @odoo-module */

import { Component, onWillUpdateProps, useEffect, useRef, useState } from "@odoo/owl";
import { useMessaging } from "../messaging_hook";
import { useEmojiPicker, loadEmojiData } from "./emoji_picker";

export class Composer extends Component {
    setup() {
        this.messaging = useMessaging();
        this.ref = useRef("textarea");
        this.caretLocationBeforeAddingEmoji = null;
        this.state = useState({
            autofocus: 0,
            value: this.props.message ? this.convertBrToLineBreak(this.props.message.body) : "",
        });
        useEmojiPicker("emoji-picker", {
            onSelect: (str) => this.addEmoji(str),
            preventClickPropagation: true,
        });
        useEffect(
            (focus) => {
                if (focus && this.ref.el) {
                    this.ref.el.focus();
                    if(this.caretLocationBeforeAddingEmoji) {
                        this.ref.el.setSelectionRange(this.caretLocationBeforeAddingEmoji, this.caretLocationBeforeAddingEmoji);
                        this.caretLocationBeforeAddingEmoji = null;
                    }
                }
            },
            () => [this.props.autofocus + this.state.autofocus, this.props.placeholder]
        );
        onWillUpdateProps(({ message }) => {
            this.state.value = message ? this.convertBrToLineBreak(message.body) : "";
        });
    }

    convertBrToLineBreak(str) {
        return new DOMParser().parseFromString(
            str.replaceAll("<br>", "\n").replaceAll("</br>", "\n"),
            "text/html"
        ).body.textContent;
    }

    onKeydown(ev) {
        loadEmojiData();
        if (ev.key === "Enter") {
            ev.preventDefault(); // to prevent useless return
            if (this.props.message) {
                this.editMessage();
            } else {
                this.sendMessage();
            }
        } else if (ev.key === "Escape") {
            this.props.onDiscardCallback();
        }
    }

    async sendMessage() {
        const el = this.ref.el;
        if (el.value.trim()) {
            await this.messaging.postMessage(
                this.props.threadId,
                el.value,
                this.props.type === "note"
            );
            if (this.props.onPostCallback) {
                this.props.onPostCallback();
            }
        }
        this.state.value = "";
        el.focus();
    }

    async editMessage() {
        const el = this.ref.el;
        if (el.value.trim()) {
            await this.messaging.updateMessage(this.props.message.id, this.ref.el.value);
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
        this.caretLocationBeforeAddingEmoji = this.ref.el.selectionStart;
    }
}

Object.assign(Composer, {
    defaultProps: { type: "message", mode: "normal", onDiscardCallback: () => {} }, // mode = compact, normal, extended
    props: [
        "threadId?",
        "message?",
        "autofocus?",
        "onDiscardCallback?",
        "onPostCallback?",
        "mode?",
        "placeholder?",
        "type?",
    ],
    template: "mail.composer",
});
