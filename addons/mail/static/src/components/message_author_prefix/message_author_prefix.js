/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class MessageAuthorPrefixView extends Component {

    /**
     * @returns {MessageAuthorPrefixView}
     */
    get messageAuthorPrefixView() {
        return this.props.record;
    }

}

Object.assign(MessageAuthorPrefixView, {
    props: { record: Object },
    template: 'mail.MessageAuthorPrefixView',
});

registerMessagingComponent(MessageAuthorPrefixView);
