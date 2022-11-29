/** @odoo-module */

import { AutoresizeInput } from "./autoresize_input";
import { Sidebar } from "./sidebar";
import { Thread } from "../thread/thread";
import { ThreadIcon } from "./thread_icon";
import { useMessageHighlight, useMessaging } from "../messaging_hook";
import { Composer } from "../composer/composer";
import { CallUI } from "../rtc/call_ui";
import { Component, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { CallSettings } from "../rtc/call_settings";
import { usePopover } from "@web/core/popover/popover_hook";

export class Discuss extends Component {
    setup() {
        this.messaging = useMessaging();
        this.messageHighlight = useMessageHighlight();
        this.contentRef = useRef("content");
        this.popover = usePopover();
        this.closePopover = null;
        this.settingsRef = useRef("settings");
        onWillStart(() => this.messaging.isReady);
        onMounted(() => (this.messaging.state.discuss.isActive = true));
        onWillUnmount(() => (this.messaging.state.discuss.isActive = false));
    }

    get thread() {
        return this.messaging.state.threads[this.messaging.state.discuss.threadId];
    }

    unstarAll() {
        this.messaging.unstarAll();
    }
    startCall() {
        this.messaging.startCall(this.messaging.state.discuss.threadId);
    }

    toggleSettings() {
        if (this.closePopover) {
            this.closePopover();
            this.closePopover = null;
        } else {
            const el = this.settingsRef.el;
            this.closePopover = this.popover.add(el, CallSettings);
        }
    }

    async renameThread({ value: name }) {
        const newName = name.trim();
        if (
            newName !== this.thread.name &&
            ((newName && this.thread.type === "channel") ||
                this.thread.type === "chat" ||
                this.thread.type === "group")
        ) {
            await this.messaging.notifyThreadNameToServer(this.thread.id, newName);
        }
    }

    async updateThreadDescription({ value: description }) {
        const newDescription = description.trim();
        if (newDescription !== this.thread.description) {
            await this.messaging.notifyThreadDescriptionToServer(this.thread.id, newDescription);
        }
    }
}

Object.assign(Discuss, {
    components: { AutoresizeInput, Sidebar, Thread, ThreadIcon, Composer, CallUI, CallSettings },
    props: ["*"],
    template: "mail.discuss",
});
