/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageContextHeaderView extends Component {

    /**
     * @returns {MessageContextHeaderView}
     */
    get messageContextHeaderView() {
        return this.props.record;
    }

}

Object.assign(MessageContextHeaderView, {
    props: { record: Object },
    template: 'mail.MessageContextHeaderView',
});

registerMessagingComponent(MessageContextHeaderView);
