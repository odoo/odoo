import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";
import { rpc } from "@web/core/network/rpc";

import { EventBus, reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const STEP_DELAY = 500;
export class ChatBotService {
    /** @type {number} */
    nextStepTimeout;

    constructor(env, services) {
        const self = reactive(this);
        self.setup(env, services);
        return self;
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * "im_livechat.livechat": import("@im_livechat/embed/common/livechat_service").LivechatService,
     * "mail.store": import("@mail/core/common/store_service").Store,
     * }} services
     */
    setup(env, services) {
        this.env = env;
        this.bus = new EventBus();
        this.livechatService = services["im_livechat.livechat"];
        this.store = services["mail.store"];
        this.livechatService.onStateChange(SESSION_STATE.NONE, () => this.stop());
        this.bus.addEventListener("MESSAGE_POST", async ({ detail: message }) => {
            await this.chatbot?.processAnswer(message);
            if (this.chatbot?.currentStep.completed) {
                this._triggerNextStep();
            }
        });
    }

    /**
     * Start the chatbot script.
     */
    async start() {
        if (this.chatbot.thread.isLastMessageFromCustomer) {
            await this.chatbot?.processAnswer(
                this.livechatService.thread.newestPersistentOfAllMessage
            );
        }
        if (!this.chatbot.currentStep?.expectAnswer || this.chatbot.currentStep?.completed) {
            this._triggerNextStep();
        }
    }

    /**
     * Stop the chatbot script.
     */
    stop() {
        clearTimeout(this.nextStepTimeout);
    }

    /**
     * Restart the chatbot script if it was completed and post the
     * restart message.
     */
    async restart() {
        if (!this.chatbot?.completed) {
            return;
        }
        const data = await rpc("/chatbot/restart", {
            channel_id: this.chatbot.thread.id,
            chatbot_script_id: this.chatbot.script.id,
        });
        const { "mail.message": messages = [] } = this.store.insert(data, { html: true });
        if (!this.livechatService.thread) {
            return;
        }
        /** @type {import("models").Message} */
        const message = messages[0];
        this.livechatService.thread.messages.add(message);
        this.chatbot.restart();
        this._triggerNextStep();
    }

    // =============================================================================
    // SCRIPT PROCESSING
    // =============================================================================

    /**
     * Trigger the next step of the script recursivly until the script is
     * completed or the current step expects an answer from the user.
     */
    async _triggerNextStep() {
        if (!this.chatbot || this.chatbot.completed) {
            return;
        }
        await this.chatbot.triggerNextStep();
        if (!this.chatbot?.currentStep) {
            return;
        }
        if (this.chatbot.currentStep.expectAnswer || this.chatbot.currentStep.isLast) {
            return;
        }
        this.nextStepTimeout = browser.setTimeout(async () => this._triggerNextStep(), STEP_DELAY);
    }

    // =============================================================================
    // GETTERS
    // =============================================================================

    get canRestart() {
        return this.chatbot?.completed && !this.chatbot.currentStep?.operatorFound;
    }

    get inputEnabled() {
        if (!this.chatbot || this.chatbot.currentStep?.operatorFound) {
            return true;
        }
        return (
            !this.chatbot.currentStep?.completed &&
            !this.isTyping &&
            this.chatbot.currentStep?.expectAnswer &&
            this.chatbot.currentStep?.answers.length === 0
        );
    }

    get inputDisabledText() {
        if (this.inputEnabled) {
            return "";
        }
        if (this.chatbot.completed) {
            return _t("Conversation ended...");
        }
        if (
            this.chatbot.currentStep?.type === "question_selection" &&
            !this.chatbot.currentStep.completed
        ) {
            return _t("Select an option above");
        }
        return _t("Say something");
    }

    get chatbot() {
        return this.livechatService.thread?.chatbot;
    }
}

export const chatBotService = {
    dependencies: ["im_livechat.livechat", "mail.store"],
    start(env, services) {
        return new ChatBotService(env, services);
    },
};
registry.category("services").add("im_livechat.chatbot", chatBotService);
