/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentImageView extends Component {

    /**
     * @returns {AttachmentImageView}
     */
    get attachmentImageView() {
        return this.props.record;
    }

}

Object.assign(AttachmentImageView, {
    props: { record: Object },
    template: 'mail.AttachmentImageView',
});

registerMessagingComponent(AttachmentImageView);
