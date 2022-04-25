/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, replace, insert, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMemberListView',
    identifyingFields: [['chatWindowOwner', 'threadViewOwner']],
    lifecycleHooks: {
        _created() {
            this.fetchChannelMembers();
        }
    },
    recordMethods: {
        async fetchChannelMembers(maxId) {
            const channelPartnersList = await this.env.services.rpc({
                route: '/mail/thread/members',
                params: {
                    channel_id: this.channel.id,
                    limit: 30,
                    max_id: maxId,
                },
            }, { shadow: true });
            this.channel.update({ memberCount: channelPartnersList.count });
            for (const channelPartner of channelPartnersList.members) {
                const relation = { channel: replace(this.channel) };
                if (channelPartner.partner) {
                    relation.partner = insertAndReplace(channelPartner.partner);
                } else {
                    relation.guest = insertAndReplace(channelPartner.guest);
                }
                this.channel.update({ channelPartners: insert(relation) });
            }
        },
        async loadMore() {
            const channelPartnerIds = this.channel
                  .channelPartners
                  .map(
                      (channelPartner) => channelPartner.id
                  );
            this.fetchChannelMembers(Math.max(...channelPartnerIds));
        },
        async onScroll() {
            if (this.isScrollEnd()) {
                await this.loadMore();
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannel() {
            if (this.chatWindowOwner) {
                return replace(this.chatWindowOwner.thread.channelOwner);
            }
            if (this.threadViewOwner) {
                return replace(this.threadViewOwner.thread.channelOwner);
            }
            return clear();
        },
        isScrollEnd() {
            if (!this.component || !this.component.root || !this.component.root.el) {
                return;
            }
            return this.component.root.el.offsetHeight + this.component.root.el.scrollTop >= this.component.root.el.scrollHeight - 150;
        },
    },
    fields: {
        channel: one('Channel', {
            compute: '_computeChannel',
            readonly: true,
        }),
        component: attr(),
        chatWindowOwner: one('ChatWindow', {
            inverse: 'channelMemberListView',
            readonly: true,
        }),
        threadViewOwner: one('ThreadView', {
            inverse: 'channelMemberListView',
            readonly: true,
        }),
    },
});
