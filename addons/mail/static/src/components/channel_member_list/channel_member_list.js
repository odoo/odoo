/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMemberListView extends Component {

    /**
     * @returns {ChannelMemberListView}
     */
    get channelMemberListView() {
        return this.props.record;
    }

}

Object.assign(ChannelMemberListView, {
    props: { record: Object },
    template: 'mail.ChannelMemberListView',
});

registerMessagingComponent(ChannelMemberListView);
