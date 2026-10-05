import { ChatWindow } from "@mail/core/common/chat_window_model";

import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChatWindow} */
const chatWindowPatch = {
    setup() {
        super.setup(...arguments);
        /** @type {PromiseWithResolvers<boolean>} */
        this.confirmCloseResolver = null;
        /** @type {PromiseWithResolvers<void>} */
        this.feedbackDoneResolver = null;
    },
    async _canClose() {
        if (!this.exists() || this.channel?.channel_type !== "livechat") {
            return super._canClose(...arguments);
        }
        if (
            !this.channel.livechatShouldAskLeaveConfirmation ||
            this.confirmCloseResolver ||
            this.feedbackDoneResolver
        ) {
            this.confirmCloseResolver = null;
            return true;
        }
        if (!this.isOpen) {
            this.open();
        }
        this.confirmCloseResolver = Promise.withResolvers();
        return this.confirmCloseResolver.promise.finally(() => (this.confirmCloseResolver = null));
    },
    async _onBeforeClose() {
        const canClose = await super._onBeforeClose(...arguments);
        if (
            !this.exists() ||
            this.channel?.channel_type !== "livechat" ||
            this.channel.isTransient ||
            this.feedbackDoneResolver ||
            !canClose
        ) {
            return canClose;
        }
        // REVIEW [3/5, correctness]: the embed version required
        // `self_member_id?.livechat_member_type === "visitor"` before taking the visitor path. Now
        // anyone not *proven* to differ from the visitor falls through: if `livechatVisitorMember`
        // is undefined (e.g. the portal/internal visitor used the allowed "leave" action in the
        // backend, so their member is gone), the agent closing the window calls
        // `/im_livechat/visitor_leave_session` (`_close_livechat_session`) and gets the visitor
        // rating panel instead of closing.
        //
        // Fix direction: branch explicitly on the self member type for the visitor flow.
        if (this.channel.livechatVisitorMember?.persona?.notEq(this.store.self)) {
            await this.channel.leaveChannelRpc();
            return canClose;
        }
        rpc("/im_livechat/visitor_leave_session", { channel_id: this.channel.id });
        this.channel.chatbot?.stop();
        this.feedbackDoneResolver = Promise.withResolvers();
        return await this.feedbackDoneResolver.promise.finally(
            () => (this.feedbackDoneResolver = null)
        );
    },
};
patch(ChatWindow.prototype, chatWindowPatch);
