/** @odoo-module */

import { qweb as QWeb } from 'web.core';
import { DocumentSelector } from '@web_editor/components/media_dialog/document_selector';
import { TABS, MediaDialog } from '@web_editor/components/media_dialog/media_dialog';
import { patch } from '@web/core/utils/patch';

/**
 * Override the @see DocumentSelector to manage files in a @see MediaDialog used
 * by the /file command. The purpose of this override is to redefine the
 * rendering of the media (/file block), and to merge images in the documents
 * tab of the MediaDialog, since the /file block displays a default mimetype for
 * every files.
 */
export class KnowledgeDocumentSelector extends DocumentSelector {
    /**
     * Filter files for the documents tab of the MediaDialog. Any file with a
     * mimetype is valid. (images and documents are displayed together)
     *
     * @override
     */
    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        return domain.map(d => {
            if (d[0] === 'mimetype') {
                return ['mimetype', '!=', false];
            }
            return d;
        });
    }

    static async createElements(...args) {
        const files = await DocumentSelector.createElements(...args);
        return files.map(file => {
            const extension = (file.title && file.title.split('.').pop()) || file.dataset.mimetype;
            const fileEl = $(QWeb.render('knowledge.file_block', {
                img: {
                    name: file.title,
                    extension: extension,
                },
            }))[0];
            file.classList.add(...DocumentSelector.mediaSpecificClasses);
            fileEl.querySelector('.o_knowledge_file_image').replaceChildren(file);
            return fileEl;
        });
    }
}
KnowledgeDocumentSelector.mediaSpecificClasses = [];
KnowledgeDocumentSelector.tagNames = DocumentSelector.tagNames;

patch(TABS, 'knowledge_media_dialog_tabs', {
    KNOWLEDGE_DOCUMENTS: {
        ...TABS.DOCUMENTS,
        id: 'KNOWLEDGE_DOCUMENTS',
        Component: KnowledgeDocumentSelector,
    }
});

patch(MediaDialog.prototype, 'knowledge_media_dialog', {
    /**
     * @override
     */
    addTabs() {
        this._super(...arguments);

        if (this.props.knowledgeDocuments) {
            this.addTab(TABS.KNOWLEDGE_DOCUMENTS);
        }
    }
});
