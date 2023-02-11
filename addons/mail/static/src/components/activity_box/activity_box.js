/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ActivityBox extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Chatter}
     */
    get chatter() {
        return this.messaging.models['mail.chatter'].get(this.props.chatterLocalId);
    }

}

Object.assign(ActivityBox, {
    props: {
        chatterLocalId: String,
    },
    template: 'mail.ActivityBox',
});

registerMessagingComponent(ActivityBox);
