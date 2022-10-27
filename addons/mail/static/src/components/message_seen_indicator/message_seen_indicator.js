/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
