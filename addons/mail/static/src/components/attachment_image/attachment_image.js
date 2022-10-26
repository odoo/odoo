/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentImage extends Component {

    /**
     * @returns {AttachmentImage}
     */
    get attachmentImage() {
        return this.props.record;
    }

}

Object.assign(AttachmentImage, {
    props: { record: Object },
    template: 'mail.AttachmentImage',
});

registerMessagingComponent(AttachmentImage);
