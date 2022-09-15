/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentCardView extends Component {

    /**
     * @returns {AttachmentCardView}
     */
    get attachmentCardView() {
        return this.props.record;
    }

}

Object.assign(AttachmentCardView, {
    props: { record: Object },
    template: 'mail.AttachmentCardView',
});

registerMessagingComponent(AttachmentCardView);
