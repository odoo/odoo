/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMemberList extends Component {

    /**
     * @returns {Thread}
     */
    get channel() {
        return this.messaging.models['Thread'].get(this.props.channelLocalId);
    }

    /**
     * @returns {ChannelMemberListView}
     */
     get channelMemberListView() {
        return this.messaging && this.messaging.models['ChannelMemberListView'].get(this.props.localId);
    }

}

Object.assign(ChannelMemberList, {
    props: {
        channelLocalId: String,
        localId: String,
    },
    template: 'mail.ChannelMemberList',
});

registerMessagingComponent(ChannelMemberList);
