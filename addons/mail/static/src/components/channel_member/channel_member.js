/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMember extends Component {

    /**
     * @returns {Thread}
     */
    get channel() {
        return this.props.channel;
    }

    /**
     * @returns {ChannelMemberView}
     */
    get record() {
        return this.props.record;
    }

}

Object.assign(ChannelMember, {
    props: {
        channel: Object,
        record: Object,
    },
    template: 'mail.ChannelMember',
});

registerMessagingComponent(ChannelMember);
