import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.livechat_operator_id = Record.one("Persona");
        this.livechatVisitorMember = Record.one("discuss.channel.member", {
            compute() {
                if (this.channel_type !== "livechat") {
                    return;
                }
                // For livechat threads, the correspondent is the first
                // channel member that is not the operator.
                const orderedChannelMembers = [...this.channel_member_ids].sort(
                    (a, b) => a.id - b.id
                );
                const isFirstMemberOperator = orderedChannelMembers[0]?.persona.eq(
                    this.livechat_operator_id
                );
                const visitor = isFirstMemberOperator
                    ? orderedChannelMembers[1]
                    : orderedChannelMembers[0];
                return visitor;
            },
        });
    },
    get autoOpenChatWindowOnNewMessage() {
        return this.channel_type === "livechat" || super.autoOpenChatWindowOnNewMessage;
    },
    get showCorrespondentCountry() {
        if (this.channel_type === "livechat") {
            return (
                this.livechat_operator_id?.eq(this.store.self) && Boolean(this.correspondentCountry)
            );
        }
        return super.showCorrespondentCountry;
    },
    get typesAllowingCalls() {
        return super.typesAllowingCalls.concat(["livechat"]);
    },

    get isChatChannel() {
        return this.channel_type === "livechat" || super.isChatChannel;
    },
});
