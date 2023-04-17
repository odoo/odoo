/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { useVisible } from "@mail/utils/common/hooks";

import { Component, useState, useSubEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {string} [emptyText]
 * @property {import("@mail/core/common/message_model").Message[]} messages
 * @property {ReturnType<import('@mail/core/common/message_search_hook').useMessageSearch>} [messageSearch]
 * @property {function} [loadMore]
 * @property {string} mode
 * @property {function} [onClickJump]
 * @property {function} [onClickUnpin]
 * @property {function} [onLoadMoreVisible]
 * @property {boolean} [showEmpty]
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class MessageCardList extends Component {
    static components = { Message };
    static props = [
        "emptyText?",
        "messages",
        "messageSearch?",
        "loadMore?",
        "mode",
        "onClickJump?",
        "onClickUnpin?",
        "onLoadMoreVisible?",
        "showEmpty?",
        "thread",
    ];
    static template = "mail.MessageCardList";

    setup() {
        this.ui = useState(useService("ui"));
        useSubEnv({ messageCard: true });
        this.loadMore = useVisible("load-more", () => this.props.onLoadMoreVisible?.());
    }

    /**
     * Highlight the given message and scrolls to it. In small mode, the
     * pin/search menus are closed beforewards
     *
     * @param {import('@mail/core/common/message_model').Message} message
     */
    async onClickJump(message) {
        this.props.onClickJump?.();
        if (this.ui.isSmall || this.env.inChatWindow) {
            this.env.pinMenu?.close();
            this.env.searchMenu?.close();
        }
        // Give the time for menus to close before scrolling to the message.
        await new Promise((resolve) => setTimeout(() => requestAnimationFrame(resolve)));
        await this.env.messageHighlight?.highlightMessage(message, this.props.thread);
    }

    get emptyText() {
        return this.props.emptyText ?? _t("No messages found");
    }
}
