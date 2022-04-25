/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMemberList extends Component {

    /**
     * @returns {ChannelMemberListView}
     */
    get channelMemberListView() {
        return this.props.record;
    }

}

Object.assign(ChannelMemberList, {
    props: { record: Object },
    template: 'mail.ChannelMemberList',
});

registerMessagingComponent(ChannelMemberList);
