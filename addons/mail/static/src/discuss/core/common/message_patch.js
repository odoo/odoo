import { Message } from "@mail/core/common/message";
import { MessageSeenIndicator } from "@mail/discuss/core/common/message_seen_indicator";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

Message.components = { ...Message.components, MessageSeenIndicator };

/** @type {Message} */
const messagePatch = {
    get repliesIndicatorTitle() {
        const numReplies = this.props.message.child_ids_count;
        return numReplies === 1 ? _t("1 Reply") : _t("%(count)s Replies", { count: numReplies });
    },
    get showMessageInReply() {
        return (
            super.showMessageInReply &&
            (!this.env.inMessageRepliesPanel ||
                !this.env.messageReplies?.message?.eq(this.props.message.parent_id))
        );
    },
    get quickActionCount() {
        return this.env.inMessageRepliesPanel ? 2 : super.quickActionCount;
    },
};
patch(Message.prototype, messagePatch);
