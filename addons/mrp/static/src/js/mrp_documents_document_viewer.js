odoo.define('mrp.MrpDocumentViewer', function (require) {
"use strict";

const DocumentViewer = require('@mail/js/document_viewer')[Symbol.for("default")];

/**
 * This file defines the DocumentViewer for the MRP Documents Kanban view.
 */
const MrpDocumentsDocumentViewer = DocumentViewer.extend({
    init(parent, attachments, activeAttachmentID) {
        this._super(...arguments);
        this.modelName = 'mrp.document';
    },
});

return MrpDocumentsDocumentViewer;

});

