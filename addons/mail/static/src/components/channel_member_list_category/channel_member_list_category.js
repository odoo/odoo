/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
