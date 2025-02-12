/** @odoo-module **/

import { ChatGPTDialog } from '@web_editor/js/wysiwyg/widgets/chatgpt_dialog';
import { useState, status } from "@odoo/owl";
import { ancestors, descendants, unwrapContents } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { sanitize } from "@web_editor/js/editor/odoo-editor/src/utils/sanitize";

export class ChatGPTAlternativesDialog extends ChatGPTDialog {
    static template = 'web_edior.ChatGPTAlternativesDialog';
    static props = {
        ...super.props,
        originalText: String,
        originalBlocks: { type: Array, element: Element },
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

    _postprocessGeneratedContent(content) {
        const fragment = super._postprocessGeneratedContent(content);
        // Keep the block formatting of the original text, matching each
        // generated line with each block of the original text. If there are
        // more generated lines than there were blocks, use the last block type
        // for the new lines.
        const originalBlocks = this.props.originalBlocks.filter(block => (
            // Only keep lowest level blocks.
            !descendants(block).some(descendant => this.props.originalBlocks.includes(descendant))
        ));
        let originalBlock;
        const generatedLines = [...fragment.childNodes];
        for (const generatedLine of generatedLines) {
            originalBlock = originalBlocks.shift() || originalBlock;
            // Only apply the style if the original post processing didn't apply
            // a special style (ie, the generated line started with "-" so it
            // created a list).
            if (originalBlock && generatedLine.nodeName === "P") {
                if (originalBlock.nodeName === "LI") {
                    // Reconstruct the list structure.
                    const listStructure = ancestors(originalBlock, this.editable)
                        .filter(ancestor => ["LI", "UL", "OL"].includes(ancestor.nodeName))
                        .reverse();
                    listStructure.push(originalBlock);
                    let listStructureParent;
                    for (const listStructureElement of listStructure) {
                        const clone = listStructureElement.cloneNode();
                        if (listStructureParent) {
                            listStructureParent.append(clone);
                        } else {
                            generatedLine.before(clone);
                        }
                        listStructureParent = clone;
                        if (listStructureElement === originalBlock) {
                            listStructureParent.append(...generatedLine.childNodes);
                            generatedLine.remove();
                        }
                    }
                } else {
                    const clone = originalBlock.cloneNode();
                    generatedLine.before(clone);
                    clone.append(...generatedLine.childNodes);
                    generatedLine.remove();
                }
            }
        }
        // Sanitize the content (so lists get merged together etc.)
        let body = document.createElement("div");
        body.setAttribute("contenteditable", "true");
        body.append(...fragment.childNodes);
        body = sanitize(body);
        fragment.append(...body.childNodes);
        // If the generated content is a single nested list, un-nest it.
        if (fragment.childElementCount === 1 && fragment.firstChild.matches("ul, ol")) {
            while ([...fragment.firstChild.children].every(child => child.matches("li.oe-nested"))) {
                for (const nestedLi of fragment.firstChild.children) {
                    unwrapContents(nestedLi);
                }
                unwrapContents(fragment.firstChild);
            }
        }
        return fragment;
    }
}
