import { AND, Record } from "@mail/core/common/record";
import { markup } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";

export class Chatbot extends Record {
    static id = AND("script", "thread");
    static MESSAGE_DELAY = 1500;
    // Time to wait without user input before considering a multi line step as
    // completed.
    static MULTILINE_STEP_DEBOUNCE_DELAY = 10000;

    isTyping = false;
    script = Record.one("ChatbotScript");
    currentStep = Record.one("ChatbotStep");
    steps = Record.many("ChatbotStep");
    thread = Record.one("Thread", { inverse: "chatbot" });
    typingMessage = Record.one("Message", {
        compute() {
            if (this.isTyping && this.thread) {
                return {
                    id: -0.1 - this.thread.id,
                    thread: this.thread,
                    author: this.script.partner,
                };
            }
        },
    });
    /**
     * @type {(message: import("models").Message) => Promise<void>}
     */
    _processAnswerDebounced = Record.attr(null, {
        compute() {
            return debounce(
                this._processAnswer,
                this.script.isLivechatTourRunning ? 500 : Chatbot.MULTILINE_STEP_DEBOUNCE_DELAY
            );
        },
    });

    /**
     * @param {import("models").Message} message
     */
    async processAnswer(message) {
        if (this.thread.notEq(message.thread) || !this.currentStep?.expectAnswer) {
            return;
        }
        if (this.currentStep.type === "free_input_multi") {
            await this._processAnswerDebounced(message);
        }
        await this._processAnswer(message);
    }

    async triggerNextStep() {
        if (this.currentStep) {
            await this._simulateTyping();
        }
        await this._goToNextStep();
        if (!this.currentStep || this.currentStep.completed) {
            return;
        }
        this.currentStep.message = this._store.Message.insert(
            this.currentStep.message ?? {
                id: this._store.env.services["mail.message"].getNextTemporaryId(),
                author: this.script.partner,
                body: this.currentStep.scriptStep.message,
                thread: this.thread,
            },
            { html: true }
        );
        if (this.currentStep.message) {
            this.thread.messages.add(this.currentStep.message);
        }
    }

    get completed() {
        return (
            (this.currentStep?.isLast &&
                (!this.currentStep.expectAnswer || this.currentStep?.completed)) ||
            this.currentStep?.operatorFound
        );
    }

    /**
     * Go to the next step of the chatbot, fetch it if needed.
     */
    async _goToNextStep() {
        if (!this.thread || this.currentStep?.isLast) {
            return;
        }
        if (this.steps.at(-1)?.eq(this.currentStep)) {
            const nextStep = await rpc("/chatbot/step/trigger", {
                channel_id: this.thread.id,
                chatbot_script_id: this.script.id,
            });
            if (!nextStep) {
                this.currentStep.isLast = true;
                return;
            }
            this.steps.push(nextStep);
        }
        const nextStepIndex = this.steps.lastIndexOf(this.currentStep) + 1;
        this.currentStep = this.steps[nextStepIndex];
    }

    /**
     * Simulate the typing of the chatbot.
     */
    async _simulateTyping() {
        this.isTyping = true;
        await new Promise((res) =>
            setTimeout(() => {
                this.isTyping = false;
                res();
            }, Chatbot.MESSAGE_DELAY)
        );
    }

    async _processAnswer(message) {
        let stepCompleted = true;
        if (this.currentStep.type === "question_email") {
            stepCompleted = await this._processAnswerQuestionEmail();
        } else if (this.currentStep.type === "question_selection") {
            stepCompleted = await this._processAnswerQuestionSelection(message);
        }
        this.currentStep.completed = stepCompleted;
    }

    /**
     * Process the user answer for a question selection step.
     *
     * @param {import("models").Message} message Answer posted by the user.
     * @returns {Promise<boolean>} Whether the script is ready to go to the next step.
     */
    async _processAnswerQuestionSelection(message) {
        const answer = this.currentStep.answers.find(({ label }) => message.body.includes(label));
        this.currentStep.selectedAnswer = answer;
        await rpc("/chatbot/answer/save", {
            channel_id: this.thread.id,
            message_id: this.currentStep.message.id,
            selected_answer_id: answer.id,
        });
        if (!answer.redirectLink) {
            return true;
        }
        let isRedirecting = false;
        if (answer.redirectLink && URL.canParse(answer.redirectLink, window.location.href)) {
            const url = new URL(window.location.href);
            const nextURL = new URL(answer.redirectLink, window.location.href);
            isRedirecting = url.pathname !== nextURL.pathname || url.origin !== nextURL.origin;
        }
        const targetURL = new URL(answer.redirectLink, window.location.origin);
        const redirectionAlreadyDone = targetURL.href === location.href;
        if (!redirectionAlreadyDone) {
            browser.location.assign(answer.redirectLink);
        }
        return redirectionAlreadyDone || !isRedirecting;
    }

    /**
     * Process the user answer for a question email step.
     *
     * @returns {Promise<boolean>} Whether the script is ready to go to the next step.
     */
    async _processAnswerQuestionEmail() {
        const { success, posted_message: message } = await rpc("/chatbot/step/validate_email", {
            channel_id: this.thread.id,
        });
        if (message) {
            this.thread.messages.add({ ...message, body: markup(message.body) });
        }
        return success;
    }

    /**
     * Restart the chatbot script.
     */
    restart() {
        if (this.currentStep) {
            this.currentStep.isLast = false;
        }
    }
}
Chatbot.register();
