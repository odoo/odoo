import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup();
        this.hasEveryoneSeen = fields.Attr(false, {
            /** @this {import("models").Message} */
            compute() {
                return this.thread?.membersThatCanSeen.every((m) => m.hasSeen(this));
            },
        });
        this.hasNewMessageSeparator = fields.Attr(false, {
            compute() {
                // compute for caching the value and not re-rendering all
                // messages when new_message_separator changes
                return this.thread?.self_member_id?.new_message_separator === this.id;
            },
        });
        this.hasSomeoneFetched = fields.Attr(false, {
            /** @this {import("models").Message} */
            compute() {
                return this.thread?.channel?.channel_member_ids.some(
                    (m) => m.persona.notEq(this.author) && m.fetched_message_id?.id >= this.id
                );
            },
        });
        this.hasSomeoneSeen = fields.Attr(false, {
            /** @this {import("models").Message} */
            compute() {
                return this.thread?.membersThatCanSeen
                    .filter((member) => member.persona.notEq(this.author))
                    .some((m) => m.hasSeen(this));
            },
        });
        this.isMessagePreviousToLastSelfMessageSeenByEveryone = fields.Attr(false, {
            /** @this {import("models").Message} */
            compute() {
                if (!this.thread?.lastSelfMessageSeenByEveryone) {
                    return false;
                }
                return this.id < this.thread.lastSelfMessageSeenByEveryone.id;
            },
        });
        /** @type {Promise<Thread>[]} @deprecated */
        this.mentionedChannelPromises = [];
        this.threadAsFirstUnread = fields.One("mail.thread", { inverse: "firstUnreadMessage" });
    },
    /** @returns {import("models").ChannelMember[]} */
    get channelMemberHaveSeen() {
        return this.thread.membersThatCanSeen.filter(
            (m) => m.hasSeen(this) && m.persona.notEq(this.author)
        );
    },
    /**
     * @override
     */
    async edit(
        body,
        attachments = [],
        { mentionedChannels = [], mentionedPartners = [], mentionedRoles = [] } = {}
    ) {
        return await super.edit(body, attachments, {
            mentionedChannels,
            mentionedPartners,
            mentionedRoles,
        });
    },
};
patch(Message.prototype, messagePatch);
