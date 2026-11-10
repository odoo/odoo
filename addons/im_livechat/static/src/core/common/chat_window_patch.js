import { CloseConfirmation } from "@im_livechat/core/common/close_confirmation";
import { FeedbackPanel } from "@im_livechat/core/common/feedback_panel";

import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { CloseConfirmation, FeedbackPanel });

patch(ChatWindow.prototype, {
    get composerHiddenContainerClass() {
        return { ...super.composerHiddenContainerClass, "px-2": this.showGiveFeedbackBtn };
    },
    get showGiveFeedbackBtn() {
        if (this.channel.selfMemberType === "visitor") {
            return this.channel.chatbot?.completed || this.channel.livechat_end_dt;
        }
        return false;
    },
    get showBlankBeforeComposerHiddenText() {
        return this.channel?.channel_type === "livechat"
            ? !this.showGiveFeedbackBtn
            : super.showBlankBeforeComposerHiddenText;
    },
    get showNeedactionCounter() {
        if (this.channel.selfMemberType === "visitor") {
            return super.showNeedactionCounter && !this.channel.chatbot;
        }
        return super.showNeedactionCounter;
    },
});
