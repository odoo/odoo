odoo.define('mrp.MrpDocumentViewer', function (require) {
"use strict";

const DocumentViewer = require('mail.DocumentViewer');

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

