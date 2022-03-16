/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentCard extends Component {

    /**
     * @returns {AttachmentCard}
     */
    get attachmentCard() {
        return this.messaging && this.messaging.models['AttachmentCard'].get(this.props.localId);
    }

}

Object.assign(AttachmentCard, {
    props: { localId: String },
    template: 'mail.AttachmentCard',
});

registerMessagingComponent(AttachmentCard);
