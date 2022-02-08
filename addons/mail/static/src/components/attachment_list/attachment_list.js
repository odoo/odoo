/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentList extends Component {

    /**
     * @returns {AttachmentList}
     */
    get attachmentList() {
        return this.messaging && this.messaging.models['AttachmentList'].get(this.props.localId);
    }

}

Object.assign(AttachmentList, {
    props: { localId: String },
    template: 'mail.AttachmentList',
});

registerMessagingComponent(AttachmentList);
