/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMemberList extends Component {

    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'ChannelMemberListView' });
    }

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
