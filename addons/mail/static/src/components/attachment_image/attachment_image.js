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
    defaultProps: {
        imageSize: '200x200',
        isEditable: true,
    },
    props: {
        attachmentImageLocalId: String,
        /**
         * Image size in server format (eg. 200x200)
         */
        imageSize: {
            type: String,
            validate: imageSize => {
                return imageSize.split('x').every(n => Number.isInteger(Number(n)));
            }
        },
        isEditable: Boolean,
    },
    template: 'mail.AttachmentImage',
});

registerMessagingComponent(AttachmentImage);
