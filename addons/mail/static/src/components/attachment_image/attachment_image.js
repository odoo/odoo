/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
const { Component } = owl;

export class AttachmentImage extends Component {

    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'mail.attachment_image', propNameAsRecordLocalId: 'attachmentImageLocalId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment_image}
     */
    get attachmentImage() {
        return this.messaging && this.messaging.models['mail.attachment_image'].get(this.props.attachmentImageLocalId);
    }

}

Object.assign(AttachmentImage, {
    props: {
        attachmentImageLocalId: String,
    },
    template: 'mail.AttachmentImage',
});

registerMessagingComponent(AttachmentImage);
