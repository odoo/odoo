/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMemberList extends Component {

    /**
     * @returns {ChannelMemberListView}
     */
     get channelMemberListView() {
        return this.messaging && this.messaging.models['ChannelMemberListView'].get(this.props.localId);
    }

}

Object.assign(ChannelMemberList, {
    props: { localId: String },
    template: 'mail.ChannelMemberList',
});

registerMessagingComponent(ChannelMemberList);
