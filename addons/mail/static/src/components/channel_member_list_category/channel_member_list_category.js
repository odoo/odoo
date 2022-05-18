/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMemberListCategory extends Component {

    /**
     * @returns {ChannelMemberListCategoryView}
     */
    get record() {
        return this.props.record;
    }

}

Object.assign(ChannelMemberListCategory, {
    props: { record: Object },
    template: 'mail.ChannelMemberListCategory',
});

registerMessagingComponent(ChannelMemberListCategory);
