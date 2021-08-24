/** @odoo-module **/

import DocumentViewer from '@mail/js/document_viewer';

/**
 * This file defines the DocumentViewer for the MRP Documents Kanban view.
 */
const MrpDocumentsDocumentViewer = DocumentViewer.extend({
    init(parent, attachments, activeAttachmentID) {
        this._super(...arguments);
        this.modelName = 'mrp.document';
    },
});

export default MrpDocumentsDocumentViewer;
