/** @odoo-module */

import { registry } from "@web/core/registry";
import { Sidebar } from "./sidebar";
import { Thread } from "../thread/thread";
import { ThreadIcon } from "./thread_icon";
import { useMessaging } from "../messaging_hook";
import { Composer } from "../composer/composer";
import { CallUI } from "../rtc/call_ui";
import { Component, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

export class Discuss extends Component {
    setup() {
        this.messaging = useMessaging();
        onWillStart(() => this.messaging.isReady);
        onMounted(() => (this.messaging.discuss.isActive = true));
        onWillUnmount(() => (this.messaging.discuss.isActive = false));
    }

    currentThread() {
        return this.messaging.threads[this.messaging.discuss.threadId];
    }

    unstarAll() {
        this.messaging.unstarAll();
    }
    startCall() {
        this.messaging.startCall(this.messaging.discuss.threadId);
    }
}

Object.assign(Discuss, {
    components: { Sidebar, Thread, ThreadIcon, Composer, CallUI },
    props: ["*"],
    template: "mail.discuss",
});

registry.category("actions").add("mail.action_discuss", Discuss);
