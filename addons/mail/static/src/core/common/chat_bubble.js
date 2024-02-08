/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";

import { Component, onWillStart, useState } from "@odoo/owl";

import { Transition } from "@web/core/transition";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ChatBubblePreview extends Component {
    static components = { Transition };
    static props = ["thread", "showPreview"];
    static template = "mail.ChatBubblePreview";

    get previewContent() {
        const lastMessage = this.props.thread.newestPersistentNotEmptyOfAllMessage;
        if (!lastMessage) {
            return false;
        }
        const selfAuthored = user.partnerId === lastMessage.author.id;
        return _t("%(authorName)s: %(body)s", {
            authorName: selfAuthored ? "You" : lastMessage.author.name,
            body: lastMessage.inlineBody,
        });
    }
}

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ChatBubble extends Component {
    static components = { ImStatus, ChatBubblePreview };
    static props = ["bubble"];
    static template = "mail.ChatBubble";

    setup() {
        this.store = useState(useService("mail.store"));
        this.threadService = useService("mail.thread");
        this.chatWindowService = useState(useService("mail.chat_window"));
        this.state = useState({ showPreview: false });
        onWillStart(async () => {
            await this.store.channels.fetch();
        });
    }

    toggleShowPreview() {
        this.state.showPreview = !this.state.showPreview;
    }

    onClickOpen() {
        this.chatWindowService.open(this.props.bubble.thread);
    }

    onClickClose(event) {
        this.chatWindowService.closeBubble(this.props.bubble);
        event.stopPropagation();
    }
}
