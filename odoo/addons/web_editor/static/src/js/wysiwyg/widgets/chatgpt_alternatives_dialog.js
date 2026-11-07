/** @odoo-module **/

import { ChatGPTDialog } from '@web_editor/js/wysiwyg/widgets/chatgpt_dialog';
import { useState, status } from "@odoo/owl";

export class ChatGPTAlternativesDialog extends ChatGPTDialog {
    static template = 'web_edior.ChatGPTAlternativesDialog';
    static props = {
        ...super.props,
        originalText: String,
        alternativesModes: { type: Object, optional: true },
        numberOfAlternatives: { type: Number, optional: true },
    };
    static defaultProps = {
        alternativesModes: {
            correct: 'Correct',
            short: 'Shorten',
            long: 'Lengthen',
            friendly: 'Friendly',
            professional: 'Professional',
            persuasive: 'Persuasive',
        },
        numberOfAlternatives: 3,
    };

    setup() {
        super.setup();
        this.state = useState({
            ...this.state,
            conversationHistory: [{
                role: 'system',
                content: 'The user wrote the following text:\n' +
                    '<generated_text>' + this.props.originalText + '</generated_text>\n' +
                    'Your goal is to help the user write alternatives to that text.\n' +
                    'Conditions:\n' +
                    '- You must respect the format (wrapping the alternative between <generated_text> and </generated_text>)\n' +
                    '- You must detect the language of the text given to you and respond in that language\n' +
                    '- Do not write HTML\n' +
                    '- You must suggest one and only one alternative per answer\n' +
                    '- Your answer must be different every time, never repeat yourself\n' +
                    '- You must respect whatever extra conditions the user gives you\n',
            }],
            messages: [],
            alternativesMode: '',
            messagesInProgress: 0,
            currentBatchId: null,
        });
        this._generationIndex = 0;
        this._generateAlternatives();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    switchAlternativesMode(ev) {
        this.state.alternativesMode = ev.currentTarget.getAttribute('data-mode');
        this._generateAlternatives(1);
    }
    preventDialogMousedown(ev) {
        // Prevent the default behavior of a mousedown event on the dialog
        // itself so it doesn't cancel the user's text selection in the editor.
        ev.preventDefault();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    async _generateAlternatives(numberOfAlternatives = this.props.numberOfAlternatives) {
        this.state.messagesInProgress = numberOfAlternatives;
        const batchId = new Date().getTime();
        this.state.currentBatchId = batchId;
        let wasError = false;
        let messageIndex = 0;
        while (!wasError && messageIndex < numberOfAlternatives && this.state.currentBatchId === batchId) {
            this._generationIndex += 1;
            let query = messageIndex ? 'Write one alternative version of the original text.' : 'Try again another single version of the original text.';
            if (this.state.alternativesMode && !messageIndex) {
                query += ` Make it more ${this.state.alternativesMode} than your last answer.`;
            }
            if (this.state.alternativesMode === 'correct') {
                query = 'Simply correct the text, without altering its meaning in any way. Preserve whatever language the user wrote their text in.';
            }
            await this._generate(query, (content, isError) => {
                if (this.state.currentBatchId === batchId) {
                    const alternative = content.replace(/^[\s\S]*<generated_text>/, '').replace(/<\/generated_text>[\s\S]*$/, '');
                    if (isError) {
                        wasError = true;
                    } else {
                        this.state.conversationHistory.push({
                            role: 'user',
                            content: query,
                        }, {
                            role: 'assistant',
                            content,
                        });
                    }
                    this.state.messages.push({
                        author: 'assistant',
                        text: alternative,
                        isError,
                        batchId,
                        mode: this.state.alternativesMode,
                        id: new Date().getTime(),
                    });
                }
            }).catch(() => {
                if (this.state.currentBatchId === batchId) {
                    wasError = true;
                    this.state.messages = [];
                }
            });
            if (status(this) === 'destroyed') {
                return;
            }
            messageIndex += 1;
            this.state.messagesInProgress -= 1;
            if (wasError) {
                break;
            }
        }
        this.state.messagesInProgress = 0;
    }
}
