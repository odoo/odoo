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

    onImageLoad(ev) {
        const image = ev.target;
        if (image && image.height <= 30) {
            this.attachmentImage.update({ isSmallImg: true });
        }
    }
}

Object.assign(AttachmentImage, {
    props: { record: Object },
    template: 'mail.AttachmentImage',
});

registerMessagingComponent(AttachmentImage);
