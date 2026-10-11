import { Message } from "@mail/core/common/message";
import { MessageSearchState } from "@mail/core/common/message_search_hook";
import { MessageHighlightPlugin } from "@mail/core/common/message_highlight_plugin";
import { useMaybePlugin, useVisible } from "@mail/utils/common/hooks";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { Component, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessageCardList extends Component {
    static components = { Message };
    static template = "mail.MessageCardList";

    messageListRef = signal.ref();
    loadMoreRef = signal.ref();

    setup() {
        super.setup();
        this.ancestors = useAncestors({ inMessageCardList: true });
        this.store = useService("mail.store");
        this.messageHighlight = useMaybePlugin(MessageHighlightPlugin);
        this.props = useProps({
            emptyText: t.string().optional(),
            loadMore: t.boolean().optional(),
            messageSearch: t.instanceOf(MessageSearchState).optional(),
            messages: t.array(t.instanceOf(this.store["mail.message"])),
            mode: t.string(),
            onClickJump: t.function([]).optional(),
            onLoadMoreVisible: t.function([]).optional(),
            showEmpty: t.boolean().optional(),
            thread: t.instanceOf(this.store["mail.thread"]),
        });
        this.ui = useService("ui");
        useVisible(this.loadMoreRef, (isVisible) => {
            if (isVisible) {
                this.props.onLoadMoreVisible?.();
            }
        });
    }

    /**
     * Highlight the given message and scrolls to it. In small mode, the
     * panels are closed beforewards
     *
     * @param {import('@mail/core/common/message_model').Message} message
     */
    async onClickJump(message) {
        this.props.onClickJump?.();
        if (this.ui.isSmall || this.ancestors.inChatWindow || this.ancestors.inMeetingView) {
            this.ancestors.inActionPanel?.close({ closeAll: true });
            this.ancestors.inMeetingView?.openChat();
        }
        // Give the time for panels to close before scrolling to the message.
        await new Promise((resolve) => setTimeout(() => requestAnimationFrame(resolve)));
        await this.messageHighlight?.highlightMessage(message);
    }

    onClickUnpin(message) {
        (message.channel_id || message.thread)?.messageUnpin(message);
    }

    get emptyText() {
        return this.props.emptyText ?? _t("No messages found");
    }
}
