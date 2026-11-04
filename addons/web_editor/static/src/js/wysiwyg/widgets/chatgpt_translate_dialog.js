import { useState } from "@odoo/owl";
import { ChatGPTDialog } from '@web_editor/js/wysiwyg/widgets/chatgpt_dialog';

export class ChatGPTTranslateDialog extends ChatGPTDialog {
    static template = 'web_editor.ChatGPTTranslateDialog';
    static props = {
        ...super.props,
        originalText: String,
        language: String,
    };

    setup() {
        super.setup();
        this.state = useState({
            ...this.state,
            conversationHistory: [{
                role: 'system',
                content: 'You are a translation assistant. You goal is to translate text while maintaining the original format and' +
                    'respecting specific instructions. \n' +
                    'Instructions: \n' +
                    '- You must respect the format (wrapping the translated text between <generated_text> and </generated_text>)\n' +
                    '- Do not write HTML.'
            }],
            messages: [],
            translationInProgress: true,
        });
        this._translate();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    async _translate() {
        const prompt = `Translate <generated_text>${this.props.originalText}</generated_text> to ${this.props.language}`;
        const messageId = new Date().getTime();
        const conversation = { role: 'user', content: prompt };
        this.state.conversationHistory.push(conversation);
        this._generate(prompt, (content, isError) => {
            let translatedText = content.replace(/^[\s\S]*<generated_text>/, '').replace(/<\/generated_text>[\s\S]*$/, '');
            if (!this.formatContent(translatedText).length) {
                isError = true;
                translatedText = "You didn't select any text.";
            }
            this.state.translationInProgress = false;
            if (!isError) {
                // There was no error, add the response to the history.
                this.state.conversationHistory.push({ role: 'assistant', content });
            }
            this.state.messages.push({
                author: 'assistant',
                text: translatedText,
                id: messageId,
                isError,
            });
            this.state.selectedMessageId = messageId;
        });
    }
}
