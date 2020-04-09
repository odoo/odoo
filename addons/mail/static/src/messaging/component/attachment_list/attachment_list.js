odoo.define('mail.messaging.component.AttachmentList', function (require) {
'use strict';

const components = {
    Attachment: require('mail.messaging.component.Attachment'),
};

const { Component } = owl;

class AttachmentList extends Component {}

Object.assign(AttachmentList, {
    components,
    defaultProps: {
        attachmentLocalIds: [],
    },
    props: {
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
        attachmentsImageSize: {
            type: String, //['small', 'medium', 'large']
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
    },
    template: 'mail.messaging.component.AttachmentList',
});

return AttachmentList;

});
