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
                memberCount: this.record.members.length,
            }
        );
    }

}

Object.assign(ChannelMemberListCategory, {
    props: { record: Object },
    template: 'mail.ChannelMemberListCategory',
});

registerMessagingComponent(ChannelMemberListCategory);
