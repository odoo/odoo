import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.livechatWelcomeMessage = fields.One("mail.message", {
            compute() {
                if (this.hasWelcomeMessage) {
                    const livechatService = this.store.env.services["im_livechat.livechat"];
                    return {
                        id: -0.2 - this.id,
                        body: livechatService.options.default_message,
                        thread: this.thread,
                        author_id: this.livechat_agent_history_ids.sort((a, b) => a.id - b.id)[0]
                            ?.partner_id,
                    };
                }
            },
        });
        this.requested_by_operator = false;
        this.storeAsActiveVisitorLivechats = fields.One("Store", {
            /** @this {import("models").DiscussChannel} */
            compute() {
                return this.channel_type === "livechat" &&
                    !this.livechat_end_dt &&
                    (this.self_member_id?.eq(this.livechatVisitorMember) || this.isTransient)
                    ? this.store
                    : null;
            },
            inverse: "activeVisitorLivechats",
        });
    },
    get hasWelcomeMessage() {
        return this.channel_type === "livechat" && !this.chatbot && !this.requested_by_operator;
    },
    _onDeleteChatWindow() {
        if (this.isTransient && this.channel_type === "livechat") {
            this.delete();
        }
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
