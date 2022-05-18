/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { sprintf } from '@web/core/utils/strings';

const { Component } = owl;

export class ChannelMemberListCategory extends Component {

    /**
     * @returns {ChannelMemberListView}
     */
    get channelMemberListView() {
        return this.props.channelMemberListView;
    }

    /**
     * @returns {ChannelMemberListCategoryView}
     */
    get record() {
        return this.props.record;
    }

    /**
     * @returns {Partner[]}
     */
    get members() {
        if (!this.channelMemberListView.exists()) {
            return [];
        }
        if (this.props.category === 'online') {
            return this.channelMemberListView.channel.orderedOnlineMembers;
        }
        if (this.props.category === 'offline') {
            return this.channelMemberListView.channel.orderedOfflineMembers;
        }
        return [];
    }

    /**
     * @returns {string}
     */
    get title() {
        let categoryText = "";
        if (this.props.category === 'online') {
            categoryText = this.env._t("Online");
        }
        if (this.props.category === 'offline') {
            categoryText = this.env._t("Offline");
        }
        return sprintf(
            this.env._t("%(categoryText)s - %(memberCount)s"),
            {
                categoryText,
                memberCount: this.members.length,
            }
        );
    }

}

Object.assign(ChannelMemberListCategory, {
    props: {
        category: String,
        channelMemberListView: Object,
        record: Object,
    },
    template: 'mail.ChannelMemberListCategory',
});

registerMessagingComponent(ChannelMemberListCategory);
