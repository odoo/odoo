/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentList extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment_list[]}
     */
    get attachmentList() {
        return this.messaging && this.messaging.models['mail.attachment_list'].get(this.props.attachmentListLocalId);
    }

}

Object.assign(AttachmentList, {
    defaultProps: {
        isCompact: false,
   },
    props: {
        areAttachmentsEditable: {
            type: Boolean,
            optional: true,
        },
        attachmentListLocalId: String,
        attachmentsImageSize: {
            type: String,
            optional: true,
        },
        isCompact: {
            type: Boolean,
            optional: true,
        },
    },
    template: 'mail.AttachmentList',
});

registerMessagingComponent(AttachmentList);
