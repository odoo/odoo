/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageAuthorPrefix extends Component {

    /**
     * @returns {MessageAuthorPrefixView}
     */
    get messageAuthorPrefixView() {
        return this.messaging && this.messaging.models['MessageAuthorPrefixView'].get(this.props.localId);
    }

}

Object.assign(MessageAuthorPrefix, {
    props: { localId: String },
    template: 'mail.MessageAuthorPrefix',
});

registerMessagingComponent(MessageAuthorPrefix);
