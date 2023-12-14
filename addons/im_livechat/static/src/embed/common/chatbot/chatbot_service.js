/* @odoo-module */

import { Chatbot } from "@im_livechat/embed/common/chatbot/chatbot_model";
import { ChatbotStep } from "@im_livechat/embed/common/chatbot/chatbot_step_model";
import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";

import { EventBus, markup, reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";

const MESSAGE_DELAY = 1500;
// Time between two messages coming from the bot.
const STEP_DELAY = 500;
// Time to wait without user input before considering a multi line
// step as completed.
const MULTILINE_STEP_DEBOUNCE_DELAY = 10000;

export class ChatBotService {
    /** @type {import("@im_livechat/embed/common/chatbot/chatbot_model").Chatbot} */
    chatbot;
    /** @type {import("@im_livechat/embed/common/chatbot/chatbot_step_model").ChatbotStep} */
    currentStep;
    /** @type {number} */
    nextStepTimeout;
    hasPostedWelcomeSteps = false;
    isTyping = false;

    constructor(env, services) {
        const self = reactive(this);
        self.setup(env, services);
        return self;
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{
     * "im_livechat.livechat": import("@im_livechat/embed/common/livechat_service").LivechatService,
     * "mail.message": import("@mail/core/common/message_service").MessageService,
     * "mail.store": import("@mail/core/common/store_service").Store,
     * rpc: typeof import("@web/core/network/rpc_service").rpcService.start,
     * }} services
     */
    setup(env, services) {
        this.env = env;
        this.bus = new EventBus();
        this.livechatService = services["im_livechat.livechat"];
        this.messageService = services["mail.message"];
        this.store = services["mail.store"];
        this.rpc = services.rpc;

        this.debouncedProcessUserAnswer = debounce(
            this._processUserAnswer.bind(this),
            MULTILINE_STEP_DEBOUNCE_DELAY
        );
        if (this.livechatService.options.isTestChatbot) {
            this.livechatService.rule.chatbot = {
                ...this.livechatService.options.testChatbotData,
                welcomeStepIndex: this.livechatService.options.testChatbotData.welcomeSteps.length,
            };
            this.currentStep = new ChatbotStep(
                this.livechatService.options.testChatbotData.welcomeSteps.at(-1)
            );
            this.livechatService.updateSession(this.livechatService.options.testChatbotChannelData);
        }
        this.livechatService.initializedDeferred.then(() => {
            this.chatbot = this.livechatService.rule?.chatbot
                ? new Chatbot(this.livechatService.rule.chatbot)
                : undefined;
        });
        this.bus.addEventListener("MESSAGE_POST", ({ detail: message }) => {
            if (this.currentStep?.type === "free_input_multi") {
                this.debouncedProcessUserAnswer(message);
            } else {
                this._processUserAnswer(message);
            }
        });
    }

    /**
     * Start the chatbot script.
     */
    async start() {
        if (this.livechatService.options.isTestChatbot && !this.hasPostedWelcomeSteps) {
            await this.postWelcomeSteps();
            this.save();
        }
        if (this.savedState) {
            this._restore();
        }
        if (!this.currentStep?.expectAnswer) {
            this._triggerNextStep();
        } else if (this.livechatService.thread?.isLastMessageFromCustomer) {
            // Answer was posted but is yet to be processed.
            this._processUserAnswer(this.livechatService.thread.newestMessage);
        }
    }

    /**
     * Stop the chatbot script and reset its state.
     */
    stop() {
        this.clear();
        clearTimeout(this.nextStepTimeout);
        this.currentStep = null;
        this.isTyping = false;
        if (this.livechatService.rule?.chatbot) {
            this.chatbot = new Chatbot(this.livechatService.rule.chatbot);
        }
    }

    /**
     * Restart the chatbot script if it was completed and post the
     * restart message.
     */
    async restart() {
        if (!this.completed || !this.livechatService.thread) {
            return;
        }
        localStorage.removeItem(
            `im_livechat.chatbot.state.uuid_${this.livechatService.thread.uuid}`
        );
        const message = await this.rpc("/chatbot/restart", {
            channel_uuid: this.livechatService.thread.uuid,
            chatbot_script_id: this.chatbot.scriptId,
        });
        this.livechatService.thread?.messages.push({ ...message, body: markup(message.body) });
        this.currentStep = null;
        this.start();
    }

    /**
     * Save the welcome steps on the server.
     */
    async postWelcomeSteps() {
        const rawMessages = await this.rpc("/chatbot/post_welcome_steps", {
            channel_uuid: this.livechatService.thread.uuid,
            chatbot_script_id: this.chatbot.scriptId,
        });
        for (const rawMessage of rawMessages) {
            this.livechatService.thread?.messages.add({
                ...rawMessage,
                body: markup(rawMessage.body),
            });
        }
        this.hasPostedWelcomeSteps = true;
    }

    // =============================================================================
    // SCRIPT PROCESSING
    // =============================================================================

    /**
     * Trigger the next step of the script recursivly until the script
     * is completed or the current step expects an answer from the user.
     */
    _triggerNextStep() {
        if (this.completed) {
            return;
        }
        this.isTyping = !this.isRestoringSavedState;
        this.nextStepTimeout = browser.setTimeout(async () => {
            const { step, stepMessage } = await this._getNextStep();
            if (!this.active) {
                return;
            }
            this.isTyping = false;
            if (!step && this.currentStep) {
                this.currentStep.isLast = true;
                return;
            }
            if (stepMessage) {
                this.livechatService.thread?.messages.add({
                    ...stepMessage,
                    body: markup(stepMessage.body),
                });
            }
            this.currentStep = step;
            if (
                this.currentStep?.type === "question_email" &&
                this.livechatService.thread.isLastMessageFromCustomer
            ) {
                await this.validateEmail();
            }
            this.save();
            if (this.currentStep.expectAnswer) {
                return;
            }
            browser.setTimeout(() => this._triggerNextStep(), this.stepDelay);
        }, this.messageDelay);
    }

    /**
     * Get the next step to process as well as the message posted by the
     * step if any.
     *
     * @returns {Promise<{ step: ChatbotStep?, stepMessage: object?}>}
     */
    async _getNextStep() {
        if (this.currentStep?.expectAnswer) {
            return { step: this.currentStep };
        }
        if (!this.chatbot.welcomeCompleted) {
            const welcomeStep = this.chatbot.nextWelcomeStep;
            return {
                step: new ChatbotStep(welcomeStep),
                stepMessage: {
                    chatbotStep: welcomeStep,
                    id: this.messageService.getNextTemporaryId(),
                    body: welcomeStep.message,
                    res_id: this.livechatService.thread.id,
                    model: this.livechatService.thread.model,
                    author: this.livechatService.thread.operator,
                },
            };
        }
        const nextStepData = await this.rpc("/chatbot/step/trigger", {
            channel_uuid: this.livechatService.thread.uuid,
            chatbot_script_id: this.chatbot.scriptId,
        });
        const { chatbot_posted_message, chatbot_step } = nextStepData ?? {};
        return {
            step: chatbot_step ? new ChatbotStep(chatbot_step) : null,
            stepMessage: chatbot_posted_message,
        };
    }

    /**
     * Process the user answer and trigger the next step.
     *
     * @param {import("models").Message} message
     */
    async _processUserAnswer(message) {
        if (
            !this.active ||
            message.originThread.localId !== this.livechatService.thread?.localId ||
            !this.currentStep?.expectAnswer
        ) {
            return;
        }
        const answer = this.currentStep.answers.find(({ label }) => message.body.includes(label));
        const stepMessage = message.originThread.messages.findLast(
            ({ chatbotStep }) => chatbotStep?.id === this.currentStep.id
        );
        if (stepMessage) {
            stepMessage.chatbotStep.hasAnswer = true;
        }
        this.currentStep.hasAnswer = true;
        this.save();
        if (answer) {
            await this.rpc("/chatbot/answer/save", {
                channel_uuid: this.livechatService.thread.uuid,
                message_id: stepMessage.id,
                selected_answer_id: answer.id,
            });
        }
        if (answer?.redirectLink) {
            browser.location.assign(answer.redirectLink);
            return;
        }
        this._triggerNextStep();
    }

    /**
     * Validate an email step and post the validation message to the
     * thread.
     */
    async validateEmail() {
        const { success, posted_message: msg } = await this.rpc("/chatbot/step/validate_email", {
            channel_uuid: this.livechatService.thread.uuid,
        });
        this.currentStep.isEmailValid = success;
        if (msg) {
            this.livechatService.thread.messages.add({ ...msg, body: markup(msg.body) });
        }
    }

    /**
     * @param {import("models").Thread} thread
     */
    isChatbotThread(thread) {
        return thread?.operator.id === this.chatbot?.partnerId;
    }

    // =============================================================================
    // STATE MANAGEMENT
    // =============================================================================

    /**
     * Restore the chatbot from the state saved in the local storage and
     * clear outdated storage.
     */
    async _restore() {
        const { _chatbotCurrentStep, _chatbot } = this.savedState;
        this.currentStep = _chatbotCurrentStep ? new ChatbotStep(_chatbotCurrentStep) : undefined;
        this.chatbot = _chatbot ? new Chatbot(_chatbot) : undefined;
        if (this.livechatService.state !== SESSION_STATE.PERSISTED) {
            // We need to repost the welcome steps as they were not saved.
            this.chatbot.welcomeStepIndex = 0;
            this.currentStep = null;
        }
    }

    /**
     * Clear outdated storage.
     */
    async clear() {
        const chatbotStorageKey = this.livechatService.sessionCookie
            ? `im_livechat.chatbot.state.uuid_${this.livechatService.sessionCookie.uuid}`
            : "";
        for (let i = 0; i < browser.localStorage.length; i++) {
            const key = browser.localStorage.key(i);
            if (key !== chatbotStorageKey && key.includes("im_livechat.chatbot.state.uuid_")) {
                browser.localStorage.removeItem(key);
            }
        }
    }

    /**
     * Save the chatbot state in the local storage.
     */
    async save() {
        if (this.isRestoringSavedState) {
            return;
        }
        browser.localStorage.setItem(
            `im_livechat.chatbot.state.uuid_${this.livechatService.thread.uuid}`,
            JSON.stringify({
                _chatbot: this.chatbot,
                _chatbotCurrentStep: this.currentStep,
            })
        );
    }

    // =============================================================================
    // GETTERS
    // =============================================================================

    get stepDelay() {
        return this.isRestoringSavedState || this.livechatService.thread?.isLastMessageFromCustomer
            ? 0
            : STEP_DELAY;
    }

    get messageDelay() {
        return this.isRestoringSavedState | !this.currentStep ? 0 : MESSAGE_DELAY;
    }

    get active() {
        return this.available && this.isChatbotThread(this.livechatService.thread);
    }

    get available() {
        return Boolean(this.chatbot);
    }

    get completed() {
        return (
            this.currentStep?.operatorFound ||
            (this.currentStep?.isLast && !this.currentStep?.expectAnswer)
        );
    }

    get canRestart() {
        return this.completed && !this.currentStep?.operatorFound;
    }

    get inputEnabled() {
        if (!this.active || this.currentStep?.operatorFound) {
            return true;
        }
        return (
            !this.isTyping &&
            this.currentStep?.expectAnswer &&
            this.currentStep?.answers.length === 0
        );
    }

    get inputDisabledText() {
        if (this.inputEnabled) {
            return "";
        }
        if (this.completed) {
            return _t("Conversation ended...");
        }
        switch (this.currentStep?.type) {
            case "question_selection":
                return _t("Select an option above");
            default:
                return _t("Say something");
        }
    }

    get savedState() {
        const raw = browser.localStorage.getItem(
            `im_livechat.chatbot.state.uuid_${this.livechatService.sessionCookie?.uuid}`
        );
        return raw ? JSON.parse(raw) : null;
    }

    get isRestoringSavedState() {
        return this.savedState?._chatbotCurrentStep.id > this.currentStep?.id;
    }
}

export const chatBotService = {
    dependencies: ["im_livechat.livechat", "mail.message", "mail.store", "rpc"],
    start(env, services) {
        return new ChatBotService(env, services);
    },
};
registry.category("services").add("im_livechat.chatbot", chatBotService);
