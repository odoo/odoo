/** @odoo-module **/

import { ChatGPTDialog } from '@web_editor/js/wysiwyg/widgets/chatgpt_dialog';
import { useState } from "@odoo/owl";

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
            selectedMessage: null,
            conversationHistory: [{
                role: 'system',
                content: 'The user wrote the following text:\n' +
                    '<generated_text>' + this.props.originalText + '</generated_text>\n' +
                    'Your goal is to help the user write alternatives to that text.\n' +
                    'Conditions:\n' +
                    '- You must respect the format (wrapping the alternative between <generated_text> and </generated_text>)\n' +
                    '- Do not write HTML\n' +
                    '- You must suggest one and only one alternative per answer\n' +
                    '- Your answer must be different every time, never repeat yourself\n' +
                    '- You must respect whatever extra conditions the user gives you\n',
            }],
            messages: [],
            alternativesMode: '',
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
        this.state.messages = [];
        this._generateAlternatives();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    async _generateAlternatives() {
        const batchId = new Date().getTime();
        this.state.currentBatchId = batchId;
        let wasError = false;
        let messageIndex = 0;
        while (!wasError && messageIndex < this.props.numberOfAlternatives && this.state.currentBatchId === batchId) {
            this._generationIndex += 1;
            let query = messageIndex ? 'Write one alternative version of the original text.' : 'Try again another single version of the original text.';
            if (this.state.alternativesMode && !messageIndex) {
                query += ` Make it more ${this.state.alternativesMode} than your last answer.`;
            }
            await this._generate(query, (content, isError) => {
                if (this.state.currentBatchId === batchId) {
                    const alternative = content.replace(/.*<generated_text>/, '').replace(/<\/generated_text>.*/, '');
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
                    });
                }
            }).catch(() => {
                if (this.state.currentBatchId === batchId) {
                    wasError = true;
                    this.state.messages = [];
                }
            });
            messageIndex += 1;
            if (wasError) {
                break;
            }
        }
    }
}
