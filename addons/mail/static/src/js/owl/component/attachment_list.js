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
    areAttachmentsDownloadable: Boolean,
    areAttachmentsEditable: Boolean,
    attachmentLocalIds: {
        type: Array,
        element: String,
    },
    attachmentsImageSizeForBasicLayout: String, // ['small', 'medium', 'large']
    attachmentsLayout: String, // ['basic', 'card']
    haveAttachmentsLabelForCardLayout: Boolean,
};

AttachmentList.template = 'mail.component.AttachmentList';

return AttachmentList;

});
