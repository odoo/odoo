/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelMemberListCategoryView extends Component {

    /**
     * @returns {ChannelMemberListCategoryView}
     */
    get record() {
        return this.props.record;
    }

}

Object.assign(ChannelMemberListCategoryView, {
    props: { record: Object },
    template: 'mail.ChannelMemberListCategoryView',
});

registerMessagingComponent(ChannelMemberListCategoryView);
