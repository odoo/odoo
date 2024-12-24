import { AND, Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";
import { browser } from "@web/core/browser/browser";
import { debounce } from "@web/core/utils/timing";
import { escape } from "@web/core/utils/strings";

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
    thread = Record.one("Thread", {
        inverse: "chatbot",
        onDelete() {
            this.delete();
        },
    });
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
        if (!this.currentStep || this.currentStep.completed || !this.thread) {
            return;
        }
        if (this.thread.isTransient) {
            // Thread is not persisted thus messages do not exist on the server,
            // create them now on the client side.
            this.currentStep.message = this.store.Message.insert(
                {
                    id: this.store.getNextTemporaryId(),
                    author: this.script.partner,
                    body: this.currentStep.scriptStep.message,
                    thread: this.thread,
                },
                { html: true }
            );
        }
        this.thread.messages.add(this.currentStep.message);
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
            const storeData = await rpc("/chatbot/step/trigger", {
                channel_id: this.thread.id,
                chatbot_script_id: this.script.id,
            });
            if (!storeData) {
                this.currentStep.isLast = true;
                return;
            }
            const { ChatbotStep: steps } = this.store.insert(storeData, { html: true });
            this.steps.push(steps[0]);
        } else {
            const nextStepIndex = this.steps.lastIndexOf(this.currentStep) + 1;
            this.currentStep = this.steps[nextStepIndex];
        }
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
        if (this.currentStep.selectedAnswer) {
            return true;
        }
        const answer = this.currentStep.answers.find(({ name }) =>
            message.body.includes(escape(name))
        );
        this.currentStep.selectedAnswer = answer;
        await rpc("/chatbot/answer/save", {
            channel_id: this.thread.id,
            message_id: this.currentStep.message.id,
            selected_answer_id: answer.id,
        });
        if (!answer.redirect_link) {
            return true;
        }
        let isRedirecting = false;
        if (answer.redirect_link && URL.canParse(answer.redirect_link, window.location.href)) {
            const url = new URL(window.location.href);
            const nextURL = new URL(answer.redirect_link, window.location.href);
            isRedirecting = url.pathname !== nextURL.pathname || url.origin !== nextURL.origin;
        }
        const targetURL = new URL(answer.redirect_link, window.location.origin);
        const redirectionAlreadyDone = targetURL.href === location.href;
        if (!redirectionAlreadyDone) {
            browser.location.assign(answer.redirect_link);
        }
        return redirectionAlreadyDone || !isRedirecting;
    }

    /**
     * Process the user answer for a question email step.
     *
     * @returns {Promise<boolean>} Whether the script is ready to go to the next step.
     */
    async _processAnswerQuestionEmail() {
        const { success, data } = await rpc("/chatbot/step/validate_email", {
            channel_id: this.thread.id,
        });
        const { Message: messages = [] } = this.store.insert(data, { html: true });
        const [message] = messages;
        if (message) {
            this.thread.messages.add(message);
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
