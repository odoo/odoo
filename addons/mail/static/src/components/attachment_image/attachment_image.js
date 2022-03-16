/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentImage extends Component {

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
