/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { sprintf } from '@web/core/utils/strings';

const { Component } = owl;

export class ChannelMemberListCategory extends Component {

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
        if (!this.record.exists()) {
            return [];
        }
        if (this.record.channelMemberListViewOwnerAsOnline) {
            return this.record.channelMemberListViewOwnerAsOnline.channel.orderedOnlineMembers;
        }
        if (this.record.channelMemberListViewOwnerAsOffline) {
            return this.record.channelMemberListViewOwnerAsOffline.channel.orderedOfflineMembers;
        }
        return [];
    }

    /**
     * @returns {string}
     */
    get title() {
        let categoryText = "";
        if (this.record.channelMemberListViewOwnerAsOnline) {
            categoryText = this.env._t("Online");
        }
        if (this.record.channelMemberListViewOwnerAsOffline) {
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
    props: { record: Object },
    template: 'mail.ChannelMemberListCategory',
});

registerMessagingComponent(ChannelMemberListCategory);
