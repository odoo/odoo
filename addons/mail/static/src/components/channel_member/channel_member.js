/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMember extends Component {

    /**
     * @returns {ChannelMemberView}
     */
    get channelMemberView() {
        return this.props.record;
    }

}

Object.assign(ChannelMember, {
    props: {
        record: Object,
    },
    template: 'mail.ChannelMember',
});

registerMessagingComponent(ChannelMember);
