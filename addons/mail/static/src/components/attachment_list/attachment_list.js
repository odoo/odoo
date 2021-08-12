/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentList extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment[]}
     */
    get attachments() {
        return this.env.models['mail.attachment'].all().filter(attachment =>
            this.props.attachmentLocalIds.includes(attachment.localId)
        );
    }

    /**
     * @returns {mail.attachment[]}
     */
    get imageAttachments() {
        return this.attachments.filter(attachment => attachment.fileType === 'image');
    }

    /**
     * @returns {mail.attachment[]}
     */
    get nonImageAttachments() {
        return this.attachments.filter(attachment => attachment.fileType !== 'image');
    }

    /**
     * @returns {mail.attachment[]}
     */
    get viewableAttachments() {
        return this.attachments.filter(attachment => attachment.isViewable);
    }

}

Object.assign(AttachmentList, {
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
            type: String,
            optional: true,
            validate: prop => ['auto', 'card', 'hover', 'none'].includes(prop),
        },
        attachmentsImageSize: {
            type: String,
            optional: true,
            validate: prop => ['small', 'medium', 'large'].includes(prop),
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
    template: 'mail.AttachmentList',
});

registerMessagingComponent(AttachmentList, { propsCompareDepth: { attachmentLocalIds: 1 } });
