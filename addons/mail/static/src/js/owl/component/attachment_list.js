odoo.define('mail.component.AttachmentList', function (require) {
'use strict';

const Attachment = require('mail.component.Attachment');

class AttachmentList extends owl.Component {}

AttachmentList.components = {
    Attachment,
};

AttachmentList.defaultProps = {
    areAttachmentsDownloadable: false,
    areAttachmentsEditable: false,
    attachmentLocalIds: [],
    attachmentsImageSizeForBasicLayout: 'medium',
    attachmentsLayout: 'basic',
    haveAttachmentsLabelForCardLayout: true,
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
    attachmentsImageSizeForBasicLayout: {
        type: String, // ['small', 'medium', 'large']
        optional: true,
    },
    attachmentsLayout: {
        type: String, // ['basic', 'card']
        optional: true,
    },
    haveAttachmentsLabelForCardLayout: {
        type: Boolean,
        optional: true,
    },
};

AttachmentList.template = 'mail.component.AttachmentList';

return AttachmentList;

});
