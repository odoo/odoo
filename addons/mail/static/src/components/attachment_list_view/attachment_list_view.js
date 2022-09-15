/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentListView extends Component {

    /**
     * @returns {AttachmentListView}
     */
    get attachmentListView() {
        return this.props.record;
    }

}

Object.assign(AttachmentListView, {
    props: { record: Object },
    template: 'mail.AttachmentListView',
});

registerMessagingComponent(AttachmentListView);
