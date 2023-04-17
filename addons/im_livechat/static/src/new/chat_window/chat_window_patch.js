/** @odoo-module */

import { ChatWindow } from "@mail/web/chat_window/chat_window";
import { FeedbackPanel } from "../feedback_panel/feedback_panel";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

ChatWindow.components["FeedbackPanel"] = FeedbackPanel;

patch(ChatWindow.prototype, "im_livechat", {
    setup() {
        this._super(...arguments);
        this.livechatService = useService("im_livechat.livechat");
    },

    close() {
        if (this.state.activeMode === "feedback" || !this.thread.uuid) {
            this._super();
        } else {
            this.livechatService.leaveSession();
            this.state.activeMode = "feedback";
        }
    },

    /**
     * @param {number} rating
     * @param {string} feedback
     */
    sendFeedback(rating, feedback) {
        this.livechatService.sendFeedback(this.thread.uuid, rating, feedback);
    },
});
