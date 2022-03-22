/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;

export class AttachmentImage extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'AttachmentImage' });
    }

    /**
     * @returns {AttachmentImage}
     */
    get attachmentImage() {
        return this.messaging && this.messaging.models['AttachmentImage'].get(this.props.localId);
    }

}

Object.assign(AttachmentImage, {
    props: { localId: String },
    template: 'mail.AttachmentImage',
});

registerMessagingComponent(AttachmentImage);
