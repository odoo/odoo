/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
