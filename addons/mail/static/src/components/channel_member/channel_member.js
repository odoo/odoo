/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMember extends Component {

    /**
     * @returns {Thread}
     */
    get channel() {
        return this.messaging.models['Thread'].get(this.props.channelLocalId);
    }

    /**
     * @returns {Partner}
     */
    get member() {
        return this.messaging.models['Partner'].get(this.props.memberLocalId);
    }

}

Object.assign(ChannelMember, {
    props: {
        channelLocalId: String,
        memberLocalId: String,
    },
    template: 'mail.ChannelMember',
});

registerMessagingComponent(ChannelMember);
