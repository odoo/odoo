import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { fields } from "@mail/model/misc";

import { computed } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.storeAsActiveVisitorLivechats = fields.One("Store", {
            inverse: "activeVisitorLivechats",
        });
        this.assignComputed(
            "storeAsActiveVisitorLivechats",
            function computeStoreAsActiveVisitorLivechats() {
                return this.channel_type === "livechat" &&
                    !this.livechat_end_dt &&
                    (this.self_member_id?.eq(this.livechatVisitorMember) || this.isTransient)
                    ? this.store
                    : null;
            }
        );
        const shouldStartChatbot = computed(() =>
            Boolean(this.chatbot && !this.chatbot.completed && !this.livechat_end_dt)
        );
        this.onChange(
            () => [shouldStartChatbot()],
            function onChangeChatbot(shouldStart) {
                this.isLoadedPromise.then(() => {
                    if (shouldStart) {
                        this.chatbot.start();
                    } else {
                        this.chatbot?.stop();
                    }
                });
            }
        );
    },
    get livechatWelcomeMessage() {
        if (this.hasWelcomeMessage) {
            const livechatService = this.store.env.services["im_livechat.livechat"];
            return this.store["mail.message"].insert({
                id: -0.2 - this.id,
                body: livechatService.options.default_message,
                thread: this.thread,
                author_id: [
                    ...this.livechat_agent_history_ids,
                    ...this.livechat_bot_history_ids,
                ].sort((a, b) => a.id - b.id)[0]?.partner_id,
            });
        }
        return undefined;
    },
    get avatarUrl() {
        if (this.channel_type !== "livechat") {
            return super.avatarUrl;
        }
        let bestScore = -1;
        let bestMemberHistory;
        // Agents are preferred over bots, current members over former members, and higher IDs over lower IDs
        for (const memberHistory of [...this.livechat_channel_member_history_ids].sort(
            (a, b) => b.id - a.id
        )) {
            if (memberHistory.livechat_member_type === "visitor") {
                continue;
            }
            const score =
                (memberHistory.livechat_member_type === "agent" ? 4 : 0) +
                (memberHistory.member_id ? 2 : 0);
            if (score > bestScore) {
                bestScore = score;
                bestMemberHistory = memberHistory;
            }
        }
        return bestMemberHistory?.partner_id?.avatarUrl || super.avatarUrl;
    },
    get hasAttachmentPanel() {
        return this.channel_type !== "livechat" && super.hasAttachmentPanel;
    },
    get hasWelcomeMessage() {
        return this.channel_type === "livechat" && !this.chatbot;
    },
    get isLastMessageFromCustomer() {
        return this.newestPersistentOfAllMessage?.isSelfAuthored;
    },
    _onDeleteChatWindow() {
        if (this.isTransient && this.channel_type === "livechat") {
            this.delete();
        }
    },
    get composerHidden() {
        return (
            super.composerHidden ||
            this.livechat_end_dt ||
            (this.chatbot?.completed && !this.livechat_agent_history_ids.length)
        );
    },
    shouldNotifyMessageToUser() {
        return this.channel_type === "livechat" || super.shouldNotifyMessageToUser(...arguments);
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
