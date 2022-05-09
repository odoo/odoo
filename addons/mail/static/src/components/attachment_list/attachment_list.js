/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentList extends Component {

    /**
     * @returns {AttachmentList}
     */
    get attachmentList() {
        return this.props.record;
    }

}

Object.assign(AttachmentList, {
    props: { record: Object },
    template: 'mail.AttachmentList',
});

registerMessagingComponent(AttachmentList);
