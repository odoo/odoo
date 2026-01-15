import { AND, fields, Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";
import { browser } from "@web/core/browser/browser";
import { debounce } from "@web/core/utils/timing";
import { expirableStorage } from "@im_livechat/core/common/expirable_storage";

export class Chatbot extends Record {
    static id = AND("script", "thread");
    static MESSAGE_DELAY = 400;
    static TYPING_DELAY = 500;
    // Time to wait without user input before considering a multi line step as
    // completed.
    static MULTILINE_STEP_DEBOUNCE_DELAY = 10000;

    forwarded;
    isTyping = false;
    isProcessingAnswer = false;
    script = fields.One("chatbot.script");
    currentStep = fields.One("ChatbotStep", {
        onUpdate() {
            if (this.currentStep?.operatorFound) {
                this.forwarded = true;
            }
        },
    });
    steps = fields.Many("ChatbotStep");
    thread = fields.One("Thread", {
        inverse: "chatbot",
        onDelete() {
            this.delete();
        },
    });
    tmpAnswer = "";
    typingMessage = fields.One("mail.message", {
        compute() {
            if (this.isTyping && this.thread) {
                return {
                    id: -0.1 - this.thread.id,
                    thread: this.thread,
                    author_id: this.script.operator_partner_id,
                };
            }
        },
    });
    /**
     * @type {(message: import("models").Message) => Promise<void>}
     */
    _processAnswerDebounced = fields.Attr(null, {
        compute() {
            return debounce(this._processAnswer, Chatbot.MULTILINE_STEP_DEBOUNCE_DELAY);
        },
    });

    /**
     * Start the chatbot. Either from the beginning if the user just started the
     * session or from where we left off if the session was restored after a
     * page load.
     */
    async start() {
        if (this.completed) {
            return;
        }
        if (this.thread.isLastMessageFromCustomer) {
            await this.processAnswer(this.thread.newestPersistentOfAllMessage);
        }
        if (!this.currentStep?.expectAnswer || this.currentStep?.completed) {
            this._runUntilUserInputStep();
        }
    }

    stop() {
        clearTimeout(this.nextStepTimeout);
    }

    async restart() {
        if (!this.completed) {
            return;
        }
        const { store_data, message_id } = await rpc("/chatbot/restart", {
            channel_id: this.thread.id,
            chatbot_script_id: this.script.id,
        });
        this.store.insert(store_data);
        this.thread.messages.add(message_id);
        if (this.currentStep) {
            this.currentStep.isLast = false;
            this.thread.livechat_end_dt = false;
        }
        this.start();
    }

    /**
     * @param {import("models").Message} message
     */
    async processAnswer(message) {
        if (
            this.forwarded ||
            this.thread.notEq(message.thread) ||
            !this.currentStep?.expectAnswer
        ) {
            return;
        }
        if (this.currentStep.step_type === "free_input_multi") {
            await this._processAnswerDebounced(message);
        } else {
            await this._processAnswer(message);
        }
        this.isProcessingAnswer = false;
    }

    async _triggerNextStep() {
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
            this.currentStep.message = this.store["mail.message"].insert({
                id: this.store.getNextTemporaryId(),
                author_id: this.script.operator_partner_id,
                body: this.currentStep.scriptStep.message,
                thread: this.thread,
            });
        }
        if (this.currentStep.message) {
            this.thread.messages.add(this.currentStep.message);
        }
    }

    get completed() {
        return (
            (this.currentStep?.isLast &&
                (!this.currentStep.expectAnswer || this.currentStep?.completed)) ||
            this.currentStep?.operatorFound ||
            this.thread.livechat_end_dt
        );
    }

    get canRestart() {
        return this.completed && !this.currentStep?.operatorFound;
    }

    /**
     * Go to the next step of the chatbot, fetch it if needed.
     */
    async _goToNextStep() {
        if (!this.thread || this.currentStep?.isLast) {
            return;
        }
        if (this.steps.at(-1)?.eq(this.currentStep)) {
            const dataRequest = this.store.DataResponse.createRequest();
            await rpc("/chatbot/step/trigger", {
                channel_id: this.thread.id,
                chatbot_script_id: this.script.id,
                data_id: dataRequest.id,
            });
            await dataRequest._resultDef;
            if (!dataRequest.chatbot_step) {
                this.currentStep.isLast = true;
                return;
            }
            this.steps.push(dataRequest.chatbot_step);
        } else {
            const nextStepIndex = this.steps.lastIndexOf(this.currentStep) + 1;
            this.currentStep = this.steps[nextStepIndex];
            this.currentStep.selectedAnswer = null;
        }
    }

    /**
     * Trigger chat bot steps recursively until the script is completed or a user
     * input is required.
     */
    async _runUntilUserInputStep() {
        await this._triggerNextStep();
        if (
            !this.currentStep ||
            this.completed ||
            (this.currentStep.expectAnswer && !this.currentStep.completed)
        ) {
            return;
        }
        this.nextStepTimeout = browser.setTimeout(
            async () => this._runUntilUserInputStep(),
            Chatbot.TYPING_DELAY
        );
    }

    /**
     * Simulate the typing of the chatbot.
     */
    async _simulateTyping(duration = Chatbot.MESSAGE_DELAY) {
        this.isTyping = true;
        await new Promise((res) =>
            setTimeout(() => {
                this.isTyping = false;
                res();
            }, duration)
        );
    }

    async _processAnswer(message) {
        if (
            this.currentStep.step_type === "free_input_multi" &&
            this.thread.composer.composerText &&
            this.tmpAnswer !== this.thread.composer.composerText
        ) {
            return await this._delayThenProcessAnswerAgain(message);
        }
        this.tmpAnswer = "";
        let stepCompleted = true;
        if (this.currentStep.step_type === "question_email") {
            stepCompleted = await this._processAnswerQuestionEmail();
        } else if (this.currentStep.step_type === "question_selection") {
            stepCompleted = await this._processAnswerQuestionSelection(message);
        }
        this.currentStep.completed = stepCompleted;
        if (this.currentStep.completed) {
            await this._runUntilUserInputStep();
        }
    }

    async _delayThenProcessAnswerAgain(message) {
        this.tmpAnswer = this.thread.composer.composerText;
        await Promise.resolve(); // Ensure that it's properly debounced when called again
        return this._processAnswerDebounced(message);
    }

    /**
     * Process the user answer for a question selection step.
     *
     * @param {import("models").Message} message Answer posted by the user.
     * @returns {Promise<boolean>} Whether the script is ready to go to the next step.
     */
    async _processAnswerQuestionSelection(message) {
        const answer = this.currentStep.selectedAnswer;
        if (!answer?.redirect_link) {
            return true;
        }
        let isRedirecting = false;
        if (answer.redirect_link && URL.canParse(answer.redirect_link, window.location.href)) {
            const url = new URL(window.location.href);
            const nextURL = new URL(answer.redirect_link, window.location.href);
            isRedirecting = url.pathname !== nextURL.pathname || url.origin !== nextURL.origin;
        }
        const redirects = JSON.parse(
            expirableStorage.getItem("im_livechat.chatbot_redirect") ?? "[]"
        );
        const targetURL = new URL(answer.redirect_link, window.location.origin);
        const redirectionAlreadyDone =
            targetURL.href === location.href || redirects.includes(message.id);
        redirects.push(message.id);
        const ONE_DAY_TTL = 60 * 60 * 24;
        expirableStorage.setItem(
            "im_livechat.chatbot_redirect",
            JSON.stringify([...new Set(redirects)]),
            ONE_DAY_TTL
        );
        if (!redirectionAlreadyDone) {
            browser.location.assign(answer.redirect_link);
        } else if (this.store.env.services.ui.isSmall) {
            await this.store.chatHub.initPromise;
            this.store.ChatWindow.get({ thread: this.thread })?.fold();
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
        this.store.insert(data);
        return success;
    }
}
Chatbot.register();
