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
                return this.thread?.selfMember?.new_message_separator === this.id;
            },
        });
        this.hasSomeoneFetched = fields.Attr(false, {
            /** @this {import("models").Message} */
            compute() {
                return this.thread?.channel_member_ids.some(
                    (m) => (m.partner_id?.notEq(this.author) || m.guest_id?.notEq(this.author_guest_id)) && m.fetched_message_id?.id >= this.id
                );
            },
        });
        this.hasSomeoneSeen = fields.Attr(false, {
            /** @this {import("models").Message} */
            compute() {
                return this.thread?.membersThatCanSeen
                    .filter(({ partner_id, guest_id }) => partner_id?.notEq(this.author) || guest_id?.notEq(this.author_guest_id))
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
        /** @type {Promise<Thread>[]} */
        this.mentionedChannelPromises = [];
        this.threadAsFirstUnread = fields.One("Thread", { inverse: "firstUnreadMessage" });
    },
    /** @returns {import("models").ChannelMember[]} */
    get channelMemberHaveSeen() {
        return this.thread.membersThatCanSeen.filter(
            (m) => {
                return m.hasSeen(this) && (m.partner_id?.notEq(this.author) || m.guest_id?.notEq(this.author_guest_id));
            }
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
        const validChannels = (await Promise.all(this.mentionedChannelPromises)).filter(
            (channel) => channel !== undefined
        );
        const allChannels = this.store.Thread.insert([...validChannels, ...mentionedChannels]);
        super.edit(body, attachments, {
            mentionedChannels: allChannels,
            mentionedPartners,
            mentionedRoles,
        });
    },
};
patch(Message.prototype, messagePatch);
