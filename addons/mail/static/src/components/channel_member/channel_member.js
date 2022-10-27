/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMemberView extends Component {

    /**
     * @returns {ChannelMemberView}
     */
    get channelMemberView() {
        return this.props.record;
    }

}

Object.assign(ChannelMemberView, {
    props: {
        record: Object,
    },
    template: 'mail.ChannelMemberView',
});

registerMessagingComponent(ChannelMemberView);
