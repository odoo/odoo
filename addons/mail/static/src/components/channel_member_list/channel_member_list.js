/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMemberList extends Component {

    /**
     * @returns {ChannelMemberListView}
     */
    get channelMemberListView() {
        return this.messaging.models['ChannelMemberListView'].get(this.props.localId);
    }

    /**
     * @returns {Thread}
     */
    get channel() {
        return this.channelMemberListView.threadView.thread;
    }

}

Object.assign(ChannelMemberList, {
    props: { localId: String },
    template: 'mail.ChannelMemberList',
});

registerMessagingComponent(ChannelMemberList);
