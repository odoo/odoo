/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class AttachmentLinkPreview extends Component {

    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'mail.attachment_link_preview_view', propNameAsRecordLocalId: 'attachmentLinkPreviewViewLocalId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment_link_preview_view}
     */
    get attachmentLinkPreviewView() {
        return this.messaging && this.messaging.models['mail.attachment_link_preview_view'].get(this.props.attachmentLinkPreviewViewLocalId);
    }

}

Object.assign(AttachmentLinkPreview, {
    props: {
        attachmentLinkPreviewViewLocalId: String,
    },
    template: 'mail.AttachmentLinkPreview',
});

registerMessagingComponent(AttachmentLinkPreview);
