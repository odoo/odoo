/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentList extends Component {

    /**
     * @returns {AttachmentList}
     */
    get attachmentList() {
        return this.messaging && this.messaging.models['AttachmentList'].get(this.props.attachmentListLocalId);
    }

}

Object.assign(AttachmentList, {
    props: {
        attachmentListLocalId: String,
        onAttachmentRemoved: {
            type: Function,
            optional: true,
        },
    },
    template: 'mail.AttachmentList',
});

registerMessagingComponent(AttachmentList);
