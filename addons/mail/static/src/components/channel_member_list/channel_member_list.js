/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
