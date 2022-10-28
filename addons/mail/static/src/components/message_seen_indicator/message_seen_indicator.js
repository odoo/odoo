/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageSeenIndicatorView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {MessageSeenIndicatorView}
     */
     get messageSeenIndicatorView() {
        return this.props.record;
    }
}

Object.assign(MessageSeenIndicatorView, {
    props: { record: Object },
    template: 'mail.MessageSeenIndicatorView',
});

registerMessagingComponent(MessageSeenIndicatorView);
