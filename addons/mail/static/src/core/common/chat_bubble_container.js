/* @odoo-module */

import { ChatBubble } from "@mail/core/common/chat_bubble";

import { Component, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Transition } from "@web/core/transition";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ChatBubbleOption extends Component {
    static components = { Transition };
    static props = [];
    static template = "mail.ChatBubbleOption";

    setup() {
        this.chatWindowService = useState(useService("mail.chat_window"));
        this.store = useState(useService("mail.store"));
        this.state = useState({ showActions: false });
    }

    toggleShowActions() {
        this.state.showActions = !this.state.showActions;
    }

    closeBubbles() {
        for (const bubble of this.store.discuss.chatBubbles) {
            this.chatWindowService.closeBubble(bubble);
        }
    }
}

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ChatBubbleHidden extends Component {
    static components = { Transition };
    static props = [];
    static template = "mail.ChatBubbleHidden";

    setup() {
        this.chatWindowService = useState(useService("mail.chat_window"));
        this.store = useState(useService("mail.store"));
        this.state = useState({ showHidden: false });
    }

    toggleShowHidden() {
        this.state.showHidden = !this.state.showHidden;
    }

    get hidden() {
        const chatBubbleLimit = this.chatWindowService.chatBubbleLimit;
        const count = this.store.discuss.chatBubbles.length - chatBubbleLimit;
        if (count <= 0) {
            return [];
        }
        return this.store.discuss.chatBubbles.slice(0, count);
    }
}

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ChatBubbleContainer extends Component {
    static components = { ChatBubble, ChatBubbleHidden, ChatBubbleOption, Transition };
    static props = [];
    static template = "mail.ChatBubbleContainer";

    setup() {
        this.chatWindowService = useState(useService("mail.chat_window"));
        this.store = useState(useService("mail.store"));
        this.store.usingChatBubbles = true;
    }

    get visible() {
        const chatBubbleLimit = this.chatWindowService.chatBubbleLimit;
        return this.store.discuss.chatBubbles.slice(-chatBubbleLimit).reverse();
    }
}

registry.category("systray").add("mail.ChatBubbleContainer", { Component: ChatBubbleContainer });
