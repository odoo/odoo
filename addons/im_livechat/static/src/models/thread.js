/** @odoo-module **/

import { addFields, addRecordMethods, patchModelMethods, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread';

addFields('Thread', {
    /**
     * If set, current thread is a livechat.
     */
    messagingAsPinnedLivechat: one('Messaging', {
        compute: '_computeMessagingAsPinnedLivechat',
        inverse: 'pinnedLivechats',
    }),
});

addRecordMethods('Thread', {
    /**
     * @private
     * @returns {FieldCommand}
     */
    _computeMessagingAsPinnedLivechat() {
        if (!this.messaging || !this.channel || this.channel.channel_type !== 'livechat' || !this.isPinned) {
            return clear();
        }
        return this.messaging;
    },
});

patchModelMethods('Thread', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('livechat_visitor' in data && data.livechat_visitor) {
            if (!data2.members) {
                data2.members = [];
            }
            // `livechat_visitor` without `id` is the anonymous visitor.
            if (!data.livechat_visitor.id) {
                /**
                 * Create partner derived from public partner and replace the
                 * public partner.
                 *
                 * Indeed the anonymous visitor is registered as a member of the
                 * channel as the public partner in the database to avoid
                 * polluting the contact list with many temporary partners.
                 *
                 * But the issue with public partner is that it is the same
                 * record for every livechat, whereas every correspondent should
                 * actually have its own visitor name, typing status, etc.
                 *
                 * Due to JS being temporary by nature there is no such notion
                 * of polluting the database, it is therefore acceptable and
                 * easier to handle one temporary partner per channel.
                 */
                const publicPartnerIds = this.messaging.publicPartners.map(partner => partner.id);
                data2.members = data2.members.filter(partnerData => !publicPartnerIds.includes(partnerData.id));
                const partnerData = Object.assign(
                    this.messaging.models['Partner'].convertData(data.livechat_visitor),
                    { id: this.messaging.models['Partner'].getNextPublicId() }
                );
                data2.members.push(partnerData);
                data2.correspondent = partnerData;
            } else {
                const partnerData = this.messaging.models['Partner'].convertData(data.livechat_visitor);
                data2.members.push(partnerData);
                data2.correspondent = partnerData;
            }
        }
        return data2;
    },
});

patchRecordMethods('Thread', {
    /**
     * @override
     */
    getMemberName(partner) {
        if (this.channel && this.channel.channel_type === 'livechat' && partner.livechat_username) {
            return partner.livechat_username;
        }
        return this._super(partner);
    },
    /**
     * @override
     */
    _computeCorrespondent() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            // livechat correspondent never change: always the public member.
            return;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeDisplayName() {
        if (this.channel && this.channel.channel_type === 'livechat' && this.correspondent) {
            if (this.correspondent.country) {
                return `${this.correspondent.nameOrDisplayName} (${this.correspondent.country.name})`;
            }
            return this.correspondent.nameOrDisplayName;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeHasInviteFeature() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            return true;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeHasMemberListFeature() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            return true;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeIsChatChannel() {
        if (this.channel && this.channel.channel_type === 'livechat') {
            return true;
        }
        return this._super();
    },
    /**
     * @override
     */
    _getDiscussSidebarCategory() {
        if (this.channel.channel_type === 'livechat') {
            return this.messaging.discuss.categoryLivechat;
        }
        return this._super();
    }
});
