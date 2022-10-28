/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class AttachmentCard extends Component {

    /**
     * @returns {AttachmentCard}
     */
    get attachmentCard() {
        return this.props.record;
    }

}

Object.assign(AttachmentCard, {
    props: { record: Object },
    template: 'mail.AttachmentCard',
});

registerMessagingComponent(AttachmentCard);
