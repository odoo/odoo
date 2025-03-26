import { patch } from "@web/core/utils/patch";
import { Chatbot } from "../common/chatbot_model";

patch(Chatbot.prototype, {
    async _processAnswer(message) {
        if (
            this.currentStep.type === "free_input_multi" &&
            this.thread.composer.body &&
            this.tmpAnswer !== this.thread.composer.body
        ) {
            return await this._delayThenProcessAnswerAgain(message);
        }
        return super._processAnswer(message);
    },
    async _delayThenProcessAnswerAgain(message) {
        this.tmpAnswer = this.thread.composer.body;
        await Promise.resolve(); // Ensure that it's properly debounced when called again
        return this._processAnswerDebounced(message);
    },
});
