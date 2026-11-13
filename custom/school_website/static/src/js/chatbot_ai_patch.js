/** @odoo-module **/

import { Thread } from "@mail/core/common/thread_model";
import { ChatbotStep } from "@im_livechat/core/common/chatbot_step_model";
import { ChatbotScript } from "@im_livechat/core/common/chatbot_script_model";
import { Chatbot } from "@im_livechat/core/common/chatbot_model";
import { ChatWindow } from "@mail/core/common/chat_window_model";
import { ChatHub } from "@mail/core/common/chat_hub_model";
import { LivechatService } from "@im_livechat/embed/common/livechat_service";
import { patch } from "@web/core/utils/patch";
import { fields } from "@mail/core/common/record";

patch(ChatbotScript.prototype, {
    setup() {
        super.setup();
        this.use_ai = fields.Attr(false);
    },
});

patch(Thread.prototype, {
    get composerDisabled() {
        // If this is an active livechat channel powered by our AI assistant, never disable the composer!
        if (this.channel_type === "livechat" && !this.livechat_end_dt) {
            const step = this.chatbot?.currentStep;
            const botScript = this.chatbot?.script;
            if (step?.step_type === "ai_chat" || botScript?.use_ai) {
                return false;
            }
        }
        return super.composerDisabled;
    },
});

patch(ChatbotStep.prototype, {
    get expectAnswer() {
        if (this.step_type === "ai_chat") {
            return true;
        }
        return super.expectAnswer;
    },
    get answer() {
        if (this.step_type === "ai_chat") {
            return this.rawAnswer;
        }
        return super.answer;
    },
});

patch(Chatbot.prototype, {
    async _processAnswer(message) {
        if (this.currentStep?.step_type === "ai_chat") {
            // Keep AI chat conversational loop active without locking the composer
            this.tmpAnswer = "";
            this.currentStep.completed = false;
            return;
        }
        return super._processAnswer(message);
    },
});

// Prevent duplicate floating bubbles or ended sessions from cluttering the screen
patch(ChatWindow.prototype, {
    computeCanShow() {
        if (this.thread?.channel_type === "livechat") {
            // Never show ended livechat sessions as floating bubbles
            if (this.thread?.livechat_end_dt && this.hubAsFolded) {
                return false;
            }
            // Ensure only one livechat bubble is ever displayed at a time
            const chatHub = this.store?.chatHub;
            if (chatHub) {
                const livechats = [
                    ...(chatHub.opened ?? []),
                    ...(chatHub.folded ?? []),
                ].filter((cw) => cw.thread?.channel_type === "livechat");
                if (livechats.length > 1) {
                    const active = livechats.find((cw) => !cw.thread?.livechat_end_dt);
                    const toKeep = active || livechats.at(-1);
                    if (!this.eq(toKeep)) {
                        return false;
                    }
                }
            }
        }
        return super.computeCanShow();
    },
});

patch(ChatHub.prototype, {
    async _load(str) {
        await super._load(...arguments);
        this._cleanupDuplicateLivechats();
    },
    _cleanupDuplicateLivechats() {
        const livechats = [...this.opened, ...this.folded].filter(
            (cw) => cw.thread?.channel_type === "livechat"
        );
        if (livechats.length > 1) {
            const active = livechats.find((cw) => !cw.thread?.livechat_end_dt);
            const toKeep = active || livechats.at(-1);
            for (const cw of livechats) {
                if (!cw.eq(toKeep)) {
                    cw.close({ force: true });
                }
            }
        }
        // Also purge any ended folded livechats from storage
        for (const cw of [...this.folded]) {
            if (cw.thread?.channel_type === "livechat" && cw.thread?.livechat_end_dt) {
                cw.close({ force: true });
            }
        }
    },
});

patch(LivechatService.prototype, {
    async open(options = {}) {
        // Close any prior livechat windows before opening a new one
        const chatHub = this.store?.chatHub;
        if (chatHub) {
            const existing = [...chatHub.opened, ...chatHub.folded].filter(
                (cw) => cw.thread?.channel_type === "livechat"
            );
            for (const cw of existing) {
                await cw.close({ force: true });
            }
        }
        return super.open(...arguments);
    },
});
