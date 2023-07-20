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
                content: 'You are a helpful assistant, your goal is to help the user write alternatives to their text.',
            },
            {
                role: 'user',
                content:  'Consider the following text : \n' + this.props.originalText,
            },
            {
                role: 'assistant',
                content: 'Thanks for this text, what do you need me to do with it?',
            }],
            messages: [],
            alternativesMode: '',
        });
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
        let wasError = false;
        let messageIndex = 0;
        while (!wasError && messageIndex < this.props.numberOfAlternatives) {
            let query = messageIndex ? 'Write one alternative version of the original text.' : 'Try again another single version of the original text.';
            if (this.state.alternativesMode && !messageIndex) {
                query += ` Make it more ${this.state.alternativesMode} than your last answer.`;
            }
            query += messageIndex ? '' : 'The original text was : \n' + this.props.originalText;
            await this._generate(query, (content, isError) => {
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
                this.state.messages = [...this.state.messages, {
                    author: 'assistant',
                    text: content,
                    isError,
                }];
            }).catch(() => {
                wasError = true;
                this.state.messages = [];
            });
            messageIndex += 1;
            if (wasError) {
                break;
            }
        }
    }
}
