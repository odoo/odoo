/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { isEmptyBlock } from "@web_editor/js/editor/odoo-editor/src/OdooEditor";
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import { useBus } from '@web/core/utils/hooks';
import {
    isZWS,
    getDeepRange,
    getSelectedNodes,
    closestElement,
} from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { ChatGPTPromptDialog } from '@web_editor/js/wysiwyg/widgets/chatgpt_prompt_dialog';
import { useRef } from '@odoo/owl';

/**
 * This widget will extend Wysiwyg and contain all code that are specific to
 * Knowledge and that should not be included in the global Wysiwyg instance.
 *
 * Note: The utils functions of the OdooEditor are included in a different bundle
 * asset than 'web.assets_backend'. We can therefore not import them in the
 * backend code of Knowledge. This widget will be allow us to use them.
 */
export class KnowledgeWysiwyg extends Wysiwyg {
    static template = 'knowledge.KnowledgeWysiwyg';

    setup() {
        super.setup(...arguments);
        useBus(this.env.bus, 'KNOWLEDGE_WYSIWYG:HISTORY_STEP', () => this.odooEditor.historyStep());
        this.knowledgeCommentsToolbarBtnRef = useRef('knowledgeCommentsToolbarBtn');
    }

    /**
     * This function enables the user to generate an article using ChatGPT.
     * We search inside of the generated content if we have a title.
     * If we find one then we put it inside of an H1 in order to have it as the article's
     * title.
     * Otherwise we put a blank H1 in the generated content so that the user can add
     * one later.
     */
    generateArticle() {
        this.env.services.dialog.add(ChatGPTPromptDialog, {
            initialPrompt: _t('Write an article about'),
            insert: (content) => {
                const generatedContentTitle = content.querySelector('h1,h2');
                const articleTitle = document.createElement('h1');
                if (generatedContentTitle && generatedContentTitle.tagName !== 'H1') {
                    articleTitle.innerText = generatedContentTitle.innerText;
                    generatedContentTitle.replaceWith(articleTitle);
                } else if (!generatedContentTitle) {
                    articleTitle.innerHTML = '<br>';
                    content.prepend(articleTitle);
                }

                const divElement = document.createElement('div');
                divElement.appendChild(content);
                this.odooEditor.resetContent(divElement.innerHTML);
            }
        });
    }

    /**
     * Configure the new buttons added inside the knowledge toolbar.
     * @override
     * @param {*} options
     */
    _configureToolbar(options) {
        this.knowledgeCommentsToolbarBtnRef.el?.addEventListener('click', () => {
            getDeepRange(this.$editable[0], { splitText: true, select: true, correctTripleClick: true });
            const selectedNodes = getSelectedNodes(this.$editable[0])
                .filter(selectedNode => selectedNode.nodeType === Node.TEXT_NODE && closestElement(selectedNode).isContentEditable);
            this.env.bus.trigger('KNOWLEDGE:CREATE_COMMENT_THREAD', {selectedNodes});
        });
        super._configureToolbar(...arguments);
    }

    _onSelectionChange() {
        const selection = document.getSelection();
        if (selection.type === "None") {
            super._onSelectionChange(...arguments);
            return;
        }
        const selectedNodes = getSelectedNodes(this.$editable[0]);
        const btnHidden = selectedNodes.length && selectedNodes.every((node) => isZWS(node) || !closestElement(node)?.isContentEditable);
        this.knowledgeCommentsToolbarBtnRef.el?.classList.toggle('d-none', btnHidden);
        super._onSelectionChange(...arguments);
    }

    /**
     * @override
     */
    async startEdition() {
        await super.startEdition(...arguments);
        this.odooEditor.options.renderingClasses = [...this.odooEditor.options.renderingClasses, 'focused-comment'];
    }

    /**
     * Checks if the editable zone of the editor is empty.
     * @returns {boolean}
     */
    isEmpty() {
        return this.$editable[0].children.length === 1 && isEmptyBlock(this.$editable[0].firstElementChild);
    }
}
