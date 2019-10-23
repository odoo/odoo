odoo.define('mail.component.AttachmentList', function (require) {
'use strict';

const Attachment = require('mail.component.Attachment');

const { Component } = owl;

class AttachmentList extends Component {}

AttachmentList.components = { Attachment };

AttachmentList.defaultProps = {
    attachmentLocalIds: [],
};

AttachmentList.props = {
    areAttachmentsDownloadable: {
        type: Boolean,
        optional: true,
    },
    areAttachmentsEditable: {
        type: Boolean,
        optional: true,
    },
    attachmentLocalIds: {
        type: Array,
        element: String,
    },
    attachmentsDetailsMode: {
        type: String, //['auto', 'card', 'hover', 'none']
        optional: true,
    },
    showAttachmentsExtensions: {
        type: Boolean,
        optional: true,
    },
    showAttachmentsFilenames: {
        type: Boolean,
        optional: true,
    },
};

AttachmentList.template = 'mail.component.AttachmentList';

return AttachmentList;

});
