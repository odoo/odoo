/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class AttachmentLinkPreview extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * @returns {mail.attachment}
     */
    get attachmentLinkPreview() {
        return this.messaging && this.messaging.models['mail.attachment_link_preview'].get(this.props.attachmentLinkPreviewLocalId);
    }

    mounted() {
        console.log(this.attachmentLinkPreview);
    }

}

Object.assign(AttachmentLinkPreview, {
    defaultProps: {
        isCompact: false,
    },
    props: {
        attachmentLinkPreviewLocalId: String,
        isCompact: {
            type: Boolean,
            optional: true,
        },
    },
    template: 'mail.AttachmentLinkPreview',
});

registerMessagingComponent(AttachmentLinkPreview);
