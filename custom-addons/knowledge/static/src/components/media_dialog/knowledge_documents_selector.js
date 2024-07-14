/** @odoo-module */

import { DocumentSelector } from '@web_editor/components/media_dialog/document_selector';
import { TABS } from '@web_editor/components/media_dialog/media_dialog';
import { patch } from "@web/core/utils/patch";

/**
 * Override the @see DocumentSelector to manage files in a @see MediaDialog used
 * by the /file command. The purpose of this override is to merge images in the
 * documents tab of the MediaDialog, since the /file block displays a default
 * mimetype for every files.
 */
export class KnowledgeDocumentSelector extends DocumentSelector {
    /**
     * @override
     * Filter files for the documents tab of the MediaDialog. Any file with a
     * mimetype is valid. (images and documents are displayed together)
     *
     * As KnowledgeDocumentsSelector is an aggregate of multiple kinds of
     * files, images included, the domain should be adjusted with the same
     * constraints as @see image_selector.js
     */
    get attachmentsDomain() {
        const domain = super.attachmentsDomain.map(d => {
            if (d[0] === 'mimetype') {
                return ['mimetype', '!=', false];
            }
            return d;
        });
        domain.unshift('&',
            '|',
                ['url', '=', null],
                '&',
                    '!', ['url', '=like', '/%/static/%'],
                    '!', ['url', '=ilike', '/web_editor/shape/%']
        );
        domain.push('!', ['name', '=like', '%.crop']);
        return domain;
    }
}
KnowledgeDocumentSelector.mediaSpecificClasses = [];
KnowledgeDocumentSelector.tagNames = DocumentSelector.tagNames;

patch(TABS, {
    KNOWLEDGE_DOCUMENTS: {
        ...TABS.DOCUMENTS,
        id: 'KNOWLEDGE_DOCUMENTS',
        Component: KnowledgeDocumentSelector,
    }
});
