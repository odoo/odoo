import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";
import { ChatGPTDialog } from "./chatgpt_dialog";

export const DEFAULT_ALTERNATIVES_MODES = {
    correct: _t("Correct"),
    short: _t("Shorten"),
    long: _t("Lengthen"),
    friendly: _t("Friendly"),
    professional: _t("Professional"),
    persuasive: _t("Persuasive"),
};

let messageId = 0;
let nextBatchId = 0;

export class ChatGPTAlternativesDialog extends ChatGPTDialog {
    static template = "html_editor.ChatGPTAlternativesDialog";
    static props = {
        ...super.props,
        originalText: String,
        alternativesModes: { type: Object, optional: true },
        numberOfAlternatives: { type: Number, optional: true },
    };
    static defaultProps = {
        alternativesModes: DEFAULT_ALTERNATIVES_MODES,
        numberOfAlternatives: 3,
    };

    setup() {
        super.setup();
        this.state = useState({
            ...this.state,
            conversationHistory: [
                {
                    role: "system",
                    content:
                        "The user wrote the following text:\n" +
                        "<generated_text>" +
                        this.props.originalText +
                        "</generated_text>\n" +
                        "Your goal is to help the user write alternatives to that text.\n" +
                        "Conditions:\n" +
                        "- You must respect the format (wrapping the alternative between <generated_text> and </generated_text>)\n" +
                        "- You must detect the language of the text given to you and respond in that language\n" +
                        "- Do not write HTML\n" +
                        "- You must suggest one and only one alternative per answer\n" +
                        "- Your answer must be different every time, never repeat yourself\n" +
                        "- You must respect whatever extra conditions the user gives you\n",
                },
            ],
            messages: [],
            alternativesMode: "",
            messagesInProgress: 0,
            currentBatchId: null,
        });
        this._generationIndex = 0;
        this.generateAlternatives();
    }

    switchAlternativesMode(ev) {
        this.state.alternativesMode = ev.currentTarget.getAttribute("data-mode");
        this.generateAlternatives(1);
    }

    async generateAlternatives(numberOfAlternatives = this.props.numberOfAlternatives) {
        this.state.messagesInProgress = numberOfAlternatives;
        const batchId = nextBatchId++;
        this.state.currentBatchId = batchId;
        let wasError = false;
        let messageIndex = 0;
        while (
            !wasError &&
            messageIndex < numberOfAlternatives &&
            this.state.currentBatchId === batchId
        ) {
            this._generationIndex += 1;
            let query = messageIndex
                ? "Write one alternative version of the original text."
                : "Try again another single version of the original text.";
            if (this.state.alternativesMode && !messageIndex) {
                query += ` Make it more ${this.state.alternativesMode} than your last answer.`;
            }
            if (this.state.alternativesMode === "correct") {
                query =
                    "Simply correct the text, without altering its meaning in any way. Preserve whatever language the user wrote their text in.";
            }
            await this.generate(query, (content, isError) => {
                if (this.state.currentBatchId === batchId) {
                    const alternative = content
                        .replace(/^[\s\S]*<generated_text>/, "")
                        .replace(/<\/generated_text>[\s\S]*$/, "");
                    if (isError) {
                        wasError = true;
                    } else {
                        this.state.conversationHistory.push(
                            {
                                role: "user",
                                content: query,
                            },
                            {
                                role: "assistant",
                                content,
                            }
                        );
                    }
                    this.state.messages.push({
                        author: "assistant",
                        text: alternative,
                        isError,
                        batchId,
                        mode: this.state.alternativesMode,
                        id: messageId++,
                    });
                }
            }).catch(() => {
                if (this.state.currentBatchId === batchId) {
                    wasError = true;
                    this.state.messages = [];
                }
            });
            messageIndex += 1;
            this.state.messagesInProgress -= 1;
            if (wasError) {
                break;
            }
        }
        this.state.messagesInProgress = 0;
    }
}
