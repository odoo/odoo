/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageAuthorPrefix extends Component {

    /**
     * @returns {MessageAuthorPrefixView}
     */
    get messageAuthorPrefixView() {
        return this.props.record;
    }

}

Object.assign(MessageAuthorPrefix, {
    props: { record: Object },
    template: 'mail.MessageAuthorPrefix',
});

registerMessagingComponent(MessageAuthorPrefix);
